"""Recognize the shipped CLI dispatch forms without importing a target checkout."""

import ast
from pathlib import Path


def _has_dispatch(path, statements, key, handler):
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
            rows = next(node.value for node in ast.parse(source).body
                        if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name)
                        and node.target.id == "_COMMANDS")
            matches = [binding for binding in ast.literal_eval(rows) if binding[0] == key]
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


def _binds_schema_call(call, definition, *, wrapper=False):
    """Recognize the shipped synchronous functions and their explicit arguments."""
    if not isinstance(definition, ast.FunctionDef):
        return False
    args = definition.args
    if (definition.decorator_list or getattr(definition, "type_params", ())
            or args.posonlyargs or args.vararg or args.kwarg
            or any(value is not None for value in args.kw_defaults)
            or any(_contains_yield(statement) for statement in definition.body)):
        return False
    # Only the engine wrapper has a default: _build_cli_parser(parser_argv=()).
    if args.defaults and not (wrapper and len(args.args) == len(args.defaults) == 1
                              and isinstance(args.defaults[0], ast.Tuple) and not args.defaults[0].elts):
        return False
    if (len(call.args) > len(args.args) or any(isinstance(arg, ast.Starred) for arg in call.args)
            or any(keyword.arg is None for keyword in call.keywords)):
        return False
    positional = [arg.arg for arg in args.args]
    named_only = [arg.arg for arg in args.kwonlyargs]
    given = positional[:len(call.args)] + [kw.arg for kw in call.keywords]
    required = positional[:len(positional) - len(args.defaults)] + named_only
    return (len(given) == len(set(given)) and set(required) <= set(given)
            and set(given) <= set(positional + named_only))


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

    def function(statements, name):
        for node in reversed(statements):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) and node.name == name:
                return node if isinstance(node, ast.FunctionDef) else None
            if isinstance(node, (ast.Assign, ast.AnnAssign, ast.Delete)) and any(
                    isinstance(ref, ast.Name) and ref.id == name and isinstance(ref.ctx, (ast.Store, ast.Del))
                    for ref in ast.walk(node)):
                return None
        return None

    schema = read_schema("workflow_cli")
    if schema is None:
        return False
    builder = function(schema, "build_cli_parser")
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
        family = function(sources[module], name)
        if (family is None or not _binds_schema_call(call, family) or not call.args
                or ast.unparse(call.args[0]) != "subparsers" or not family.args.args
                or family.args.args[0].arg != "subparsers"):
            return False
        found = found or _declares_parser(family.body, key)
    # main receives the parser only after every mandatory registration returns.
    return found


def inspect_cli_registration(path: Path, key: str, handler: str) -> dict:
    """Observe the target's parser and actual call to its selected handler."""
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
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
    return {"main": main is not None, "handler": handler in functions,
            "argparse": has_parser, "dispatch": _has_dispatch(path, statements, key, handler)}
