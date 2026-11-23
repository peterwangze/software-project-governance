"""Recognize the shipped CLI dispatch forms without importing a target checkout."""

import ast
import sys
from pathlib import Path


_DSH_COMMANDS = {
    "dsh-doctor": "cmd_dsh_doctor",
    "check-dsh-boundary": "cmd_check_dsh_boundary",
    "check-dsh-preset-compat": "cmd_check_dsh_preset_compat",
    "check-dsh-preset-smoke": "cmd_check_dsh_preset_smoke",
}


_DSH_CALL_OWNERS = {"dsh_doctor", "dsh_compat", "host_validation_cli", "host_loader_probes",
                    "checks.dsh_smoke", "checks.dsh_boundary"}


def _handler_source(path, definition, depth=0, *, owners=_DSH_CALL_OWNERS):
    """Follow the handler's directly imported adapters in the inspected installation."""
    calls = [node for node in ast.walk(definition)
             if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)]
    for node in definition.body:
        if not isinstance(node, ast.ImportFrom) or node.module not in owners:
            continue
        if node.level:
            return False
        source = path.parent.joinpath(*node.module.split(".")).with_suffix(".py")
        try:
            statements = ast.parse(source.read_text(encoding="utf-8"), filename=str(source)).body
        except (OSError, UnicodeError, SyntaxError):
            return False
        for alias in node.names:
            provider = _local_definition(statements, alias.name)
            bound = alias.asname or alias.name
            invocations = [call for call in calls if call.func.id == bound]
            if not invocations or not all(_binds_explicit_call(call, provider) for call in invocations):
                return False
            if depth == 0 and node.module in {"host_validation_cli", "host_loader_probes"}:
                if not _handler_source(path, provider, depth + 1):
                    return False
    return True


def _final_registry_whitelist(registry):
    """Read the last literal loader set, refusing later unrecognized uses at module scope."""
    name = "LOADER_WHITELIST"
    for row in reversed(registry):
        if isinstance(row, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            if row.name == name:
                break
            continue
        if isinstance(row, (ast.Import, ast.ImportFrom)):
            if any((item.asname or item.name.split(".")[0]) == name for item in row.names):
                break
            continue
        if not any(isinstance(node, ast.Name) and node.id == name for node in ast.walk(row)):
            continue
        targets = row.targets if isinstance(row, ast.Assign) else [getattr(row, "target", None)]
        if (len(targets) == 1 and isinstance(targets[0], ast.Name) and targets[0].id == name
                and isinstance(row, (ast.Assign, ast.AnnAssign))
                and isinstance(row.value, (ast.List, ast.Tuple, ast.Set))):
            return {item.value for item in row.value.elts if isinstance(item, ast.Constant)}
        break
    return set()


def _registered_owner_definition(path, registry, module, handler, namespace_call):
    if module not in _final_registry_whitelist(registry):
        return None
    source = path.with_name(module + ".py")
    try:
        statements = ast.parse(source.read_text(encoding="utf-8"), filename=str(source)).body
    except (OSError, UnicodeError, SyntaxError):
        return False
    function = _local_definition(statements, handler)
    return function if _binds_explicit_call(namespace_call, function) else None


def _dsh_owner_is_loadable(path, registry, module, handler, namespace_call):
    function = _registered_owner_definition(path, registry, module, handler, namespace_call)
    return bool(function) and _handler_source(path, function, depth=1)


def _gate_review_is_wired(path, function):
    """Follow the scoped gate command's imported providers to its review invocation."""
    if not function:
        return False
    body = function.body[1:] if ast.get_docstring(function) else function.body
    bindings = {}
    providers = {"loop_workflow": "gate_review", "resolve_entry": "current_host_root"}
    for node in body[:2]:
        if not isinstance(node, ast.ImportFrom) or node.level or len(node.names) != 1:
            return False
        member = node.names[0]
        if providers.get(node.module) != member.name:
            return False
        bindings[member.name] = member.asname or member.name
    if len(bindings) != 2 or len(set(bindings.values())) != 2 or not function.args.args:
        return False
    # The required-arguments guard precedes the single scoped transaction.
    # Resolve the helpers at this actual call site, including local import aliases.
    if len(body) < 4 or not isinstance(body[2], ast.If) or not isinstance(body[3], ast.Try):
        return False
    first = body[3].body[0]
    if not isinstance(first, ast.Assign) or not isinstance(first.value, ast.Call):
        return False
    call = first.value
    args = function.args.args[0].arg
    if (args in bindings.values() or ast.unparse(call.func) != bindings["gate_review"] or call.keywords
            or [ast.unparse(arg) for arg in call.args] != [
                bindings["current_host_root"] + "()", args + ".unit", args + ".gate_id.upper()", args + ".review"]):
        return False
    return _handler_source(path, function, owners=providers)


def _dispatches_declared_handler(registry):
    """The parsed Namespace uses the registered path, with only the shipped DSH argv adapter."""
    loader = _local_definition(registry, "load_handler")
    if loader is None:
        return False
    body = loader.body[1:] if ast.get_docstring(loader) else loader.body
    if len(body) != 3 or ast.unparse(body[0]) != "path = command_spec(key).handler":
        return False
    adapter = body[1]
    if (not isinstance(adapter, ast.If) or adapter.orelse
            or ast.unparse(adapter.test) != "parsed_args and path == 'dsh_doctor.main'"):
        return False
    if ast.unparse(body[2]) != "return resolve_loader(path)":
        return False
    return _binds_explicit_call(body[2].value, _local_definition(registry, "resolve_loader"))


def _gate_owner_dispatch(path, registry, handler, call):
    if not _dispatches_declared_handler(registry):
        return False
    function = _registered_owner_definition(path, registry, "governance_fact_cli", handler, call)
    return _gate_review_is_wired(path, function)


def _dsh_registered_dispatch(path, key, handler, matches, registry, namespace_call):
    if key == "dsh-doctor":
        if matches != [(key, "dsh_doctor.main")]:
            return False
        loader = next((fn for fn in registry if isinstance(fn, ast.FunctionDef) and fn.name == "load_handler"), None)
        if loader is None:
            return False
        # main supplies a Namespace. Only the shipped parsed-args branch adapts
        # the argv entry; seeing dsh_doctor.main in the table alone is insufficient.
        body = loader.body[1:] if ast.get_docstring(loader) else loader.body
        if len(body) != 3 or not isinstance(body[1], ast.If) or len(body[1].body) != 1 or body[1].orelse:
            return False
        route = ast.unparse(body[1].body[0])
        return (ast.unparse(body[0]) == "path = command_spec(key).handler"
                and ast.unparse(body[1].test) == "parsed_args and path == 'dsh_doctor.main'"
                and (route == "path = 'verify_workflow.cmd_dsh_doctor'" or
                     (route == "path = 'host_validation_cli.cmd_dsh_doctor'" and
                      _dsh_owner_is_loadable(path, registry, "host_validation_cli", handler, namespace_call)))
                and ast.unparse(body[2]) == "return resolve_loader(path)")
    owner = {"check-dsh-preset-compat": "dsh_compat", "check-dsh-boundary": "host_validation_cli",
             "check-dsh-preset-smoke": "host_loader_probes"}[key]
    if matches == [(key, f"{owner}.{handler}")]:
        return _dsh_owner_is_loadable(path, registry, owner, handler, namespace_call)
    return matches == [(key, f"verify_workflow.{handler}")]

_RELEASE_COMMANDS = {
    "release-ledger": "cmd_release_ledger",
    "release-projection": "cmd_release_projection",
    "quality-tools": "cmd_quality_tools",
}


# These are the three public Namespace adapters shipped with the release CLI.
# Slots correspond to the tuple returned by the adapter's input reader.
_RELEASE_ADAPTERS = {
    "cmd_release_ledger": ("_render_ledger", "_ledger_inputs",
                           ("host_project_root", "plugin_root", "repository_context", "validate_release_ledger")),
    "cmd_release_projection": ("_render_projection", "_projection_inputs",
                               ("plugin_root", "check_projections", "write_projections")),
    "cmd_quality_tools": ("_render_quality", "_quality_probe", ("probe_quality_tools",)),
}


def _module_body(path, module):
    if not isinstance(module, str) or not all(part.isidentifier() for part in module.split(".")):
        return ()
    source = path.parent.joinpath(*module.split(".")).with_suffix(".py")
    try:
        return ast.parse(source.read_text(encoding="utf-8"), filename=str(source)).body
    except (OSError, UnicodeError, SyntaxError):
        return ()


def _release_provider_available(path, function):
    """Read the native provider's package imports and the bindings it actually returns."""
    if function is None or not function.body or not isinstance(function.body[-1], ast.Return):
        return False
    imports = set()
    for statement in function.body[:-1]:
        if not isinstance(statement, ast.ImportFrom) or statement.level or not statement.module:
            return False
        owner = _module_body(path, statement.module)
        for alias in statement.names:
            kind = ast.ClassDef if alias.name == "RepositoryContext" else ast.FunctionDef
            if _local_definition(owner, alias.name, kind) is None:
                return False
            imports.add(alias.asname or alias.name)
    value = function.body[-1].value
    members = value.elts if isinstance(value, ast.Tuple) else [value]
    for member in members:
        if isinstance(member, ast.Call) and not member.args and not member.keywords:
            member = member.func
        if not isinstance(member, ast.Name) or member.id not in imports:
            return False
    return bool(members)


def _release_module_binding(engine, name):
    """Find the last direct binding of a selected release collaborator."""
    for node in reversed(engine):
        if isinstance(node, (ast.FunctionDef, ast.ClassDef)) and node.name == name:
            return node
        if isinstance(node, (ast.Import, ast.ImportFrom)) and any(
                (item.asname or item.name.split(".")[0]) == name for item in node.names):
            return node
        if isinstance(node, (ast.Assign, ast.AnnAssign, ast.Delete)):
            targets = node.targets if hasattr(node, "targets") else [node.target]
            if any(isinstance(ref, ast.Name) and ref.id == name for target in targets for ref in ast.walk(target)):
                return node
    return None


def _release_import_available(path, engine, name, kind):
    binding = _release_module_binding(engine, name)
    if isinstance(binding, kind):
        return True
    if not isinstance(binding, ast.ImportFrom) or binding.level:
        return False
    alias = next(item for item in binding.names if (item.asname or item.name) == name)
    return _local_definition(_module_body(path, binding.module), alias.name, kind) is not None


def _release_policy_available(path, engine, expression):
    if (not isinstance(expression, ast.Call) or expression.args or expression.keywords
            or not isinstance(expression.func, ast.Call)):
        return False
    lookup = expression.func
    if (ast.unparse(lookup.func) != "_product_policy" or lookup.keywords or len(lookup.args) != 1
            or not isinstance(lookup.args[0], ast.Constant) or not isinstance(lookup.args[0].value, str)):
        return False
    name = lookup.args[0].value
    reader = _release_module_binding(engine, "_product_policy")
    if isinstance(reader, ast.Assign) and isinstance(reader.value, ast.Name):
        reader = _local_definition(engine, reader.value.id)
    if not isinstance(reader, ast.FunctionDef):
        return False
    binding = _release_module_binding(engine, "_PRODUCT_POLICY_OWNERS")
    if not isinstance(binding, ast.Assign) or not isinstance(binding.value, ast.Dict):
        return False
    owners = {key.value: value.value for key, value in zip(binding.value.keys, binding.value.values)
              if isinstance(key, ast.Constant) and isinstance(value, ast.Constant)}
    return _local_definition(_module_body(path, owners.get(name)), name) is not None


def _engine_release_inputs(path, engine, selected, keywords):
    if not isinstance(selected, ast.Lambda) or selected.args.args or selected.args.kwonlyargs:
        return False
    value = selected.body
    if keywords == ("probe_quality_tools",):
        return _release_policy_available(path, engine, value)
    if not isinstance(value, ast.Tuple) or len(value.elts) != len(keywords):
        return False
    for role, member in zip(keywords, value.elts):
        if role in ("plugin_root", "host_project_root"):
            if role == "plugin_root":
                if not isinstance(member, ast.Lambda) or member.args.args or member.args.kwonlyargs:
                    return False
                member = member.body
            if not isinstance(member, ast.Name) or not isinstance(_release_module_binding(engine, member.id), ast.Assign):
                return False
        else:
            kind = ast.ClassDef if role == "repository_context" else ast.FunctionDef
            if not isinstance(member, ast.Name) or not _release_import_available(path, engine, member.id, kind):
                return False
    return True


def _selected_release_inputs(path, engine, owner, provider, keywords):
    """The owner defaults apply unless the target actually binds other inputs for __main__."""
    for block in engine:
        if not isinstance(block, ast.Try) or not block.body or not isinstance(block.body[0], ast.ImportFrom):
            continue
        imported = block.body[0]
        binding = next((item for item in imported.names if item.name == "bind_release_commands"
                        or item.asname == "_bind_release_commands"), None)
        if binding is None:
            continue
        if imported.level or imported.module != "release_validation_cli" or binding.name != "bind_release_commands":
            return False
        binder = binding.asname or binding.name
        for guard in block.orelse:
            if not isinstance(guard, ast.If) or not isinstance(guard.test, ast.Compare):
                return False
            test = guard.test
            if ast.unparse(test.left) != "__name__" or len(test.ops) != 1:
                return False
            literal = test.comparators[0]
            if isinstance(test.ops[0], ast.In) and isinstance(literal, (ast.Tuple, ast.List, ast.Set)):
                if not all(isinstance(item, ast.Constant) for item in literal.elts):
                    return False
                active = any(item.value == "__main__" for item in literal.elts)
            elif isinstance(test.ops[0], ast.Eq) and isinstance(literal, ast.Constant):
                active = literal.value == "__main__"
            else:
                return False
            branch = guard.body if active else guard.orelse
            if not branch:
                continue
            if len(branch) != 1 or not isinstance(branch[0], ast.Expr):
                return False
            call = branch[0].value
            install = _local_definition(owner, "bind_release_commands")
            if (not isinstance(call, ast.Call) or ast.unparse(call.func) != binder
                    or not _binds_explicit_call(call, install)):
                return False
            selected = {kw.arg: kw.value for kw in call.keywords}
            command = selected.get("command")
            if not isinstance(command, ast.Name) or _local_definition(engine, command.id) is None:
                return False
            # Only the explicitly global names change the owner. Other targets
            # of the same unpacking assignment are locals and leave the native reader intact.
            body = install.body[1:] if ast.get_docstring(install) else install.body
            if not body or not all(isinstance(stmt, ast.Global) for stmt in body[:-1]):
                return False
            module_names = {name for stmt in body[:-1] for name in stmt.names}
            assignment = body[-1]
            if (not isinstance(assignment, ast.Assign) or len(assignment.targets) != 1
                    or not isinstance(assignment.targets[0], ast.Tuple) or not isinstance(assignment.value, ast.Tuple)):
                return False
            targets, values = assignment.targets[0].elts, assignment.value.elts
            if len(targets) != len(values) or not all(isinstance(item, ast.Name) for item in targets + values):
                return False
            if any(value.id not in selected for value in values):
                return False
            overrides = {target.id: value.id for target, value in zip(targets, values)
                         if target.id in module_names}
            parameter = overrides.get(provider)
            if parameter is not None:
                return _engine_release_inputs(path, engine, selected.get(parameter), keywords)
    return _release_provider_available(path, _local_definition(owner, provider))


def _release_owner_accepts(path, engine, handler, invocation):
    statements = _module_body(path, "release_validation_cli")
    function = _local_definition(statements, handler)
    if (not _binds_explicit_call(invocation, function) or not function.args.args):
        return False
    renderer, provider, keywords = _RELEASE_ADAPTERS[handler]
    body = function.body[1:] if ast.get_docstring(function) else function.body
    if not body or not isinstance(body[-1], ast.Return) or not isinstance(body[-1].value, ast.Call):
        return False
    call = body[-1].value
    if (not isinstance(call.func, ast.Name) or call.func.id != renderer
            or len(call.args) != 1 or not isinstance(call.args[0], ast.Name)
            or call.args[0].id != function.args.args[0].arg
            or not _binds_explicit_call(call, _local_definition(statements, renderer))):
        return False
    if len(keywords) == 1:
        if len(body) != 1:
            return False
        bindings = [provider]
    else:
        if len(body) != 2 or not isinstance(body[0], ast.Assign) or len(body[0].targets) != 1:
            return False
        target, reader = body[0].targets[0], body[0].value
        if (not isinstance(target, ast.Tuple) or not all(isinstance(item, ast.Name) for item in target.elts)
                or not isinstance(reader, ast.Call) or not isinstance(reader.func, ast.Name)
                or reader.func.id != provider or reader.args or reader.keywords):
            return False
        bindings = [item.id for item in target.elts]
    passed = {item.arg: item.value.id for item in call.keywords if isinstance(item.value, ast.Name)}
    return (len(bindings) == len(keywords) and len(set(bindings)) == len(bindings)
            and passed == dict(zip(keywords, bindings))
            and _selected_release_inputs(path, engine, statements, provider, keywords))


def _release_handler_is_loadable(path, engine, function):
    if function is None:
        return False
    body = function.body[1:] if ast.get_docstring(function) else function.body
    if not any(isinstance(node, ast.ImportFrom) and node.module == "release_validation_cli" for node in body):
        # The historical command implements output and validation in this file.
        return True
    if len(body) != 2 or not isinstance(body[0], ast.ImportFrom) or body[0].level or len(body[0].names) != 1:
        return False
    imported = body[0].names[0]
    result = body[1]
    if (imported.name != function.name or not isinstance(result, ast.Return)
            or not isinstance(result.value, ast.Call) or not isinstance(result.value.func, ast.Name)
            or result.value.func.id != (imported.asname or imported.name) or len(result.value.args) != 1
            or result.value.keywords or not function.args.args or not isinstance(result.value.args[0], ast.Name)
            or result.value.args[0].id != function.args.args[0].arg or result.value.args[0].id == result.value.func.id):
        return False
    return _release_owner_accepts(path, engine, function.name, result.value)


def _has_dispatch(path, engine, statements, key, handler):
    args_parsed = any(
        isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == "args" for t in node.targets)
        and isinstance(node.value, ast.Call) and ast.unparse(node.value.func) == "parser.parse_args"
        for node in statements
    )
    if not args_parsed:
        return False
    for statement in statements[:-1]:
        if any(isinstance(node, ast.Return) for node in ast.walk(statement)):
            return False
    # Both shipped engines dispatch in the final statement. A literal table
    # or a loader reference elsewhere in main does not wire a command.
    tail = statements[-1]
    if not isinstance(tail, (ast.Return, ast.Expr)) or not isinstance(tail.value, ast.Call):
        return False
    call = tail.value
    if len(call.args) != 1 or ast.unparse(call.args[0]) != "args" or call.keywords:
        return False
    target = call.func
    if ast.unparse(target) == "registry.load_handler(args.command or 'verify', parsed_args=True)":
        try:
            source = path.with_name("registry.py").read_text(encoding="utf-8")
            registry = ast.parse(source).body
            rows = next(node.value for node in registry
                        if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name)
                        and node.target.id == "_COMMANDS")
            matches = [binding for binding in ast.literal_eval(rows) if binding[0] == key]
            if (key == "gate-check" and handler == "cmd_gate_check"
                    and matches == [(key, "governance_fact_cli.cmd_gate_check")]):
                return _gate_owner_dispatch(path, registry, handler, call)
            if _DSH_COMMANDS.get(key) == handler:
                return _dsh_registered_dispatch(path, key, handler, matches, registry, call)

            if (_RELEASE_COMMANDS.get(key) == handler
                    and matches == [(key, f"release_validation_cli.{handler}")]):
                return ("release_validation_cli" in _final_registry_whitelist(registry)
                        and _dispatches_declared_handler(registry)
                        and _release_owner_accepts(path, engine, handler, call))
            return matches == [(key, f"verify_workflow.{handler}")]
        except (OSError, UnicodeError, SyntaxError, StopIteration, IndexError, KeyError, TypeError, ValueError):
            return False

    # The releases read one literal table and never touch it again before
    # dispatch. Any other use (e.g. a mutation or alias) is outside this
    # recognized form and cannot substantiate availability.
    if ast.unparse(target) not in ("commands[cmd]", "commands[args.command]"):
        return False
    if ast.unparse(target) == "commands[cmd]":
        selectors = [node for node in statements[:-1] if isinstance(node, ast.Assign)
                     and any(isinstance(name, ast.Name) and name.id == "cmd" for name in node.targets)]
        if len(selectors) != 1 or ast.unparse(selectors[0].value) != "args.command or 'verify'":
            return False
    uses = [node for node in statements[:-1]
            if any(isinstance(ref, ast.Name) and ref.id == "commands" for ref in ast.walk(node))]
    if len(uses) != 1 or not isinstance(uses[0], ast.Assign):
        return False
    assignment = uses[0]
    if (len(assignment.targets) != 1 or ast.unparse(assignment.targets[0]) != "commands"
            or not isinstance(assignment.value, ast.Dict)):
        return False
    entries = [entry for item, entry in zip(assignment.value.keys, assignment.value.values)
               if isinstance(item, ast.Constant) and item.value == key]
    return len(entries) == 1 and isinstance(entries[0], ast.Name) and entries[0].id == handler


def _declares_parser(statements, key):
    for statement in statements:
        if isinstance(statement, (ast.Return, ast.Raise)):
            break
        if not isinstance(statement, (ast.Assign, ast.Expr)):
            continue
        call = statement.value
        # Some commands attach an option directly to the returned parser.
        if isinstance(call, ast.Call) and isinstance(call.func, ast.Attribute) and call.func.attr == "add_argument":
            call = call.func.value
        if (isinstance(call, ast.Call) and ast.unparse(call.func) == "subparsers.add_parser"
                and call.args and isinstance(call.args[0], ast.Constant) and call.args[0].value == key):
            return True
    return False


def _contains_yield(node):
    if isinstance(node, (ast.Yield, ast.YieldFrom)):
        return True
    # Nested bodies have their own scope. Their defaults and decorators still
    # execute in the enclosing scope when the nested definition is reached.
    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Lambda)):
        body = node.body if isinstance(node.body, list) else [node.body]
        return any(_contains_yield(child) for child in ast.iter_child_nodes(node) if child not in body)
    return any(_contains_yield(child) for child in ast.iter_child_nodes(node))


def _binds_explicit_call(call, definition):
    """Bind explicit arguments to a directly defined synchronous callable."""
    if not isinstance(definition, ast.FunctionDef):
        return False
    args = definition.args
    if (definition.decorator_list or getattr(definition, "type_params", ())
            or args.posonlyargs or args.vararg or args.kwarg
            or any(_contains_yield(statement) for statement in definition.body)):
        return False
    if (len(call.args) > len(args.args) or any(isinstance(arg, ast.Starred) for arg in call.args)
            or any(keyword.arg is None for keyword in call.keywords)):
        return False
    positional = [arg.arg for arg in args.args]
    named_only = [arg.arg for arg in args.kwonlyargs]
    given = positional[:len(call.args)] + [kw.arg for kw in call.keywords]
    required = positional[:len(positional) - len(args.defaults)] + [
        name for name, default in zip(named_only, args.kw_defaults) if default is None]
    return (len(given) == len(set(given)) and set(required) <= set(given)
            and set(given) <= set(positional + named_only))


def _binds_schema_call(call, definition, *, wrapper=False):
    """The shipped parser families require all arguments except the wrapper's empty tuple."""
    if not _binds_explicit_call(call, definition):
        return False
    args = definition.args
    if any(default is not None for default in args.kw_defaults):
        return False
    return not args.defaults or (wrapper and len(args.args) == len(args.defaults) == 1
                                 and isinstance(args.defaults[0], ast.Tuple) and not args.defaults[0].elts)


def _local_definition(statements, name, kind=ast.FunctionDef):
    """Read the final direct definition; a later replacement is not that callable."""
    for node in reversed(statements):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) and node.name == name:
            return node if isinstance(node, kind) else None
        if isinstance(node, (ast.Assign, ast.AnnAssign, ast.Delete)) and any(
                isinstance(ref, ast.Name) and ref.id == name and isinstance(ref.ctx, (ast.Store, ast.Del))
                for ref in ast.walk(node)):
            return None
        if isinstance(node, (ast.Import, ast.ImportFrom)) and any(
                (alias.asname or alias.name.split(".")[0]) == name for alias in node.names):
            return None
    return None


def _schema_declares_parser(path, wrapper, invocation, key):
    """Follow the shipped wrapper and its called families in this checkout only."""
    body = wrapper.body
    if ast.get_docstring(wrapper) is not None:
        body = body[1:]
    if (len(body) != 2 or not _binds_schema_call(invocation, wrapper, wrapper=True)
            or ast.unparse(body[0]) != "from workflow_cli import build_cli_parser"
            or not isinstance(body[1], ast.Return) or not isinstance(body[1].value, ast.Call)
            or ast.unparse(body[1].value.func) != "build_cli_parser"):
        return False

    def read_schema(name):
        source = path.with_name(name + ".py")
        try:
            return ast.parse(source.read_text(encoding="utf-8"), filename=str(source)).body
        except (OSError, UnicodeError, SyntaxError):
            return None

    schema = read_schema("workflow_cli")
    if schema is None:
        return False
    builder = _local_definition(schema, "build_cli_parser")
    if (not builder or not _binds_schema_call(body[1].value, builder)
            or ast.unparse(builder.body[-1]) != "return (parser, subparsers)"):
        return False
    # Only the schema siblings are part of this static proof. An unconditional
    # import must exist even when the requested parser belongs to another family.
    sources = {"": schema}
    for node in schema:
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name in {"workflow_cli_checks", "workflow_cli_operations"}:
                    sibling = read_schema(alias.name)
                    if sibling is None:
                        return False
                    sources[alias.asname or alias.name] = sibling
    has_group = False
    found = False
    for statement in builder.body[:-1]:
        if isinstance(statement, (ast.Return, ast.Raise)):
            return False
        if isinstance(statement, ast.Assign) and any(ast.unparse(t) == "subparsers" for t in statement.targets):
            if has_group:
                return False
            has_group = (isinstance(statement.value, ast.Call) and
                         ast.unparse(statement.value.func) == "parser.add_subparsers")
        if not has_group or not isinstance(statement, ast.Expr) or not isinstance(statement.value, ast.Call):
            continue
        call = statement.value
        module, _, name = ast.unparse(call.func).rpartition(".")
        if module not in sources or not name.startswith("register_"):
            return False
        family = _local_definition(sources[module], name)
        if (family is None or not _binds_schema_call(call, family) or not call.args
                or ast.unparse(call.args[0]) != "subparsers" or not family.args.args
                or family.args.args[0].arg != "subparsers"):
            return False
        found = found or _declares_parser(family.body, key)
    # main receives the parser only after every mandatory registration returns.
    return found


def _delegates_to_owner(definition, module, owner_body, positional, keywords, setup=()):
    """Recognize a direct, unconditional import and return in the shipped adapters."""
    body = definition.body[1:] if ast.get_docstring(definition) is not None else definition.body
    if len(body) != len(setup) + 2:
        return False
    dependency, *assignments, result = body
    if (not isinstance(dependency, ast.ImportFrom) or dependency.level or dependency.module != module
            or not isinstance(result, ast.Return) or not isinstance(result.value, ast.Call)):
        return False
    aliases = {item.name: item.asname or item.name for item in dependency.names}
    imported = {definition.name}
    if setup:
        imported.add("SelectionPolicy")
    if set(aliases) != imported or len(set(aliases.values())) != len(dependency.names):
        return False
    call = result.value
    if (not isinstance(call.func, ast.Name) or call.func.id != aliases[definition.name]
            or not _binds_schema_call(call, _local_definition(owner_body, definition.name))
            or [ast.unparse(arg) for arg in call.args] != positional
            or {kw.arg: ast.unparse(kw.value) for kw in call.keywords} != keywords):
        return False
    # The validator prepares its local root, context and policy before the
    # return. Other adapters have no intervening statements or bindings.
    if any(not isinstance(assign, ast.Assign) or len(assign.targets) != 1
           or ast.unparse(assign.targets[0]) != name for assign, name in zip(assignments, setup)):
        return False
    if setup:
        policy = assignments[-1].value
        if (_local_definition(owner_body, "SelectionPolicy", ast.ClassDef) is None or not isinstance(policy, ast.Call)
                or ast.unparse(policy.func) != aliases["SelectionPolicy"]):
            return False
    # An import must not shadow a forwarded argument, a setup local or a
    # global supplied to the owner (e.g. "as args" would forward the function).
    forwarded = [*call.args, *(kw.value for kw in call.keywords)]
    names = {ref.id for expr in forwarded for ref in ast.walk(expr) if isinstance(ref, ast.Name)}
    return not (set(aliases.values()) & (names | set(setup)))


def _has_capability_handler(path, functions):
    """Observe the historical inline handler or the three current adapter calls."""
    handler = functions.get("cmd_capability_context")
    if handler is None:
        return False
    discover, validate = "discover_capability_context", "check_capability_context"
    if not any(isinstance(node, (ast.Import, ast.ImportFrom, ast.Return)) for node in ast.walk(handler)):
        # A locally implemented registration (including a standalone no-op)
        # needs no sibling. The shipped inline engines call both local functions.
        if len(handler.body) == 1 and isinstance(handler.body[0], ast.Pass):
            return True
        calls = {node.func.id for node in ast.walk(handler)
                 if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)}
        return {discover, validate} <= calls and discover in functions and validate in functions
    if (discover not in functions or validate not in functions or not handler.args.args
            or ast.unparse(handler.args) != handler.args.args[0].arg
            or ast.unparse(functions[discover].args) != "root=None"
            or ast.unparse(functions[validate].args) != "root=None, *, sampled_context=None"
            or any(functions[name].decorator_list for name in (handler.name, discover, validate))):
        return False
    owners = {}
    for module in ("status_cli", "capability_context"):
        sibling = path.with_name(module + ".py")
        try:
            body = ast.parse(sibling.read_text(encoding="utf-8"), filename=str(sibling)).body
        except (OSError, UnicodeError, SyntaxError):
            return False
        owners[module] = body
    paths = {"requirements_path": "CAPABILITY_CONTEXT_DOC_PATH", "tools_path": "CAPABILITY_CONTEXT_TOOLS_PATH"}
    return (
        _delegates_to_owner(handler, "status_cli", owners["status_cli"], [handler.args.args[0].arg],
                              {"plugin_root": "ROOT", "discover": discover, "validate": validate,
                               "display_path": "_display_path"})
        and _delegates_to_owner(functions[discover], "capability_context", owners["capability_context"],
                                  ["_context_root(root)"], {**paths, "check_registry": "check_capability_registry"})
        and _delegates_to_owner(functions[validate], "capability_context", owners["capability_context"],
                                  ["root", "context"], {**paths, "policy": "policy", "display_path": "_display_path"},
                                  setup=("root", "context", "policy"))
    )


def inspect_cli_registration(path: Path, key: str, handler: str) -> dict:
    """Observe the target's parser and actual call to its selected handler."""
    source = path.read_text(encoding="utf-8")
    parse = getattr(sys.modules.get("engine_source"), "parse_engine_source", None)
    tree = parse(path, source) if callable(parse) else ast.parse(source, filename=str(path))
    functions = {node.name: node for node in tree.body if isinstance(node, ast.FunctionDef)}
    main = functions.get("main")
    statements = main.body if main else []
    parser_body = statements
    schema_parser = False
    for node in statements:
        if isinstance(node, ast.Assign) and isinstance(node.value, ast.Call):
            if ast.unparse(node.value.func) == "_build_cli_parser":
                builder = functions.get("_build_cli_parser")
                parser_body = builder.body if builder else ()
                if builder is not None:
                    schema_parser = _schema_declares_parser(path, builder, node.value, key)
                break
    has_parser = _declares_parser(parser_body, key) or schema_parser
    has_handler = handler in functions
    if key == "gate-check" and handler == "cmd_gate_check":
        definition = _local_definition(tree.body, handler)
        has_handler = definition is not None
        if has_handler and any(isinstance(node, ast.ImportFrom) and node.module == "governance_fact_cli"
                               for node in definition.body):
            try:
                owner = ast.parse(path.with_name("governance_fact_cli.py").read_text(encoding="utf-8")).body
                has_handler = (not definition.decorator_list and len(definition.args.args) == 1
                               and _delegates_to_owner(definition, "governance_fact_cli", owner,
                                                         [definition.args.args[0].arg], {}))
            except (OSError, SyntaxError, UnicodeError):
                has_handler = False
    elif handler == "cmd_capability_context":
        has_handler = _has_capability_handler(path, functions)
    elif has_handler and _DSH_COMMANDS.get(key) == handler:
        definition = _local_definition(tree.body, handler)
        has_handler = definition is not None and _handler_source(path, definition)
    elif _RELEASE_COMMANDS.get(key) == handler:
        has_handler = _release_handler_is_loadable(path, tree.body, _local_definition(tree.body, handler))
    return {"main": main is not None, "handler": has_handler,
            "argparse": has_parser, "dispatch": _has_dispatch(path, tree.body, statements, key, handler)}
