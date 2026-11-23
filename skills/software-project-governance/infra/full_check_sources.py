"""Read the full-check reports bound by the engine in a supplied installation."""
import ast
import re
import sys


def parse_module_source(path, source):
    """Keep the census error contract when the inspected engine cannot be parsed."""
    parse = getattr(sys.modules.get("engine_source"), "parse_engine_source", None)
    try:
        return parse(path, source) if callable(parse) else ast.parse(source, filename=str(path))
    except SyntaxError as exc:
        raise ValueError(f"cannot parse full-check source {path}: {exc}") from exc


def _engine_functions(path, tree, names):
    functions = {}
    for statement in tree.body:
        if isinstance(statement, ast.FunctionDef) and statement.name in names:
            if statement.name in functions:
                raise ValueError(f"{path}: duplicate full-check definition {statement.name}")
            functions[statement.name] = statement
            continue
        # Follow conditional module-level bindings. Definitions introduce a
        # separate scope, so a local helper with the same name is unrelated.
        pending = [statement]
        while pending:
            node = pending.pop()
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                rebound = node.name
            elif isinstance(node, ast.Name) and isinstance(node.ctx, (ast.Store, ast.Del)):
                rebound = node.id
            elif isinstance(node, ast.alias):
                rebound = node.asname or node.name.split(".")[0]
            else:
                pending.extend(ast.iter_child_nodes(node))
                continue
            if rebound in names:
                raise ValueError(f"{path}: full-check function {rebound} is rebound")
    return functions


def _body(function):
    # A leading docstring is not an executable registration.
    statements = function.body
    return statements[1:] if ast.get_docstring(function) is not None else statements


def _module_source(path):
    try:
        source = path.read_text(encoding="utf-8")
        return source, ast.parse(source, filename=str(path))
    except SyntaxError as exc:
        raise ValueError(f"cannot parse full-check source {path}: {exc}") from exc
    except (OSError, UnicodeError) as exc:
        raise ValueError(f"cannot read full-check source {path}: {exc}") from exc


def _report_module(entry, name, installed):
    if installed is None:
        path = entry.with_name(name + ".py")
        text, tree = _module_source(path)
        return path, text, tree
    try:
        return installed.syntax(name)
    except (OSError, UnicodeError, SyntaxError) as exc:
        raise ValueError(f"{entry}: cannot read full-check module {name}: {exc}") from exc


def _plain_function(node, name, parameter):
    return (isinstance(node, ast.FunctionDef) and node.name == name
            and not node.decorator_list and node.returns is None
            and not getattr(node, "type_params", ()) and ast.unparse(node.args) == parameter)


def _verify_runner(path, module):
    """Prove this installed runner consumes every yielded count and returns their sum."""
    declarations = _body(module)
    # No other module bindings may replace the reducer, sum, or print.
    if len(declarations) != 1 or not _plain_function(declarations[0], "run_full_checks", "section_results"):
        raise ValueError(f"{path}: unsupported full-check runner definition")
    statements = _body(declarations[0])
    if (len(statements) < 2 or ast.unparse(statements[0]) != "all_issues = sum(section_results)"
            or ast.unparse(statements[-1]) != "return all_issues"):
        raise ValueError(f"{path}: full-check runner must consume and return the complete issue count")
    # Between the reduction and return the supported runner only prints text
    # and branches on its count. Reject early exits, writes, and further calls.
    output_nodes = (ast.Expr, ast.Call, ast.If, ast.Compare, ast.Eq, ast.JoinedStr,
                    ast.FormattedValue, ast.Constant, ast.Name, ast.Load)
    for statement in statements[1:-1]:
        for node in ast.walk(statement):
            if (not isinstance(node, output_nodes)
                    or isinstance(node, ast.Name) and node.id not in ("print", "all_issues")
                    or isinstance(node, ast.Call) and not (
                        isinstance(node.func, ast.Name) and node.func.id == "print")):
                raise ValueError(f"{path}: unsupported operation between the full-check sum and return")


def _governance_command_consumes(command):
    """Recognize the full arm of the shipped scope dispatch and its exit verdict."""
    if not _plain_function(command, "cmd_check_governance", "args"):
        return False
    body = _body(command)
    if len(body) != 4:
        return False
    configure, scope, routing, verdict = body
    if (not isinstance(configure, ast.Try) or configure.orelse or configure.finalbody
            or [ast.unparse(node) for node in configure.body] != ["sys.stdout.reconfigure(encoding='utf-8', errors='replace')"]
            or len(configure.handlers) != 1 or ast.unparse(configure.handlers[0]) != "except Exception:\n    pass"
            or not isinstance(scope, ast.If) or scope.orelse
            or ast.unparse(scope.test) != "getattr(args, 'scope', 'full') == 'quick'"
            or [ast.unparse(node) for node in scope.body] != ["setattr(args, 'quick', True)"]):
        return False
    if (not isinstance(routing, ast.If)
            or ast.unparse(routing.test) != "getattr(args, 'quick', False) or getattr(args, 'shadow', False)"
            or [ast.unparse(node) for node in routing.body] != [
                "from quickscan_selector import run_quick_checks",
                "all_issues, output = run_quick_checks(args, _run_full_engine_checks)", "print(output, end='')"]
            or len(routing.orelse) != 1 or not isinstance(routing.orelse[0], ast.If)):
        return False
    summary = routing.orelse[0]
    return (ast.unparse(summary.test) == "getattr(args, 'summary_only', False)"
            and [ast.unparse(node) for node in summary.body[:2]] == [
                "buf = io.StringIO()", "with redirect_stdout(buf):\n    all_issues = _run_full_engine_checks(args)"]
            and [ast.unparse(node) for node in summary.orelse] == ["all_issues = _run_full_engine_checks(args)"]
            and isinstance(verdict, ast.If) and not verdict.orelse
            and ast.unparse(verdict.test) == "getattr(args, 'fail_on_issues', False) and all_issues > 0"
            and [ast.unparse(node) for node in verdict.body] == ["sys.exit(1)"])


def _declaration(module, name):
    """Read a single directly bound declaration, rejecting replaced values."""
    candidates = [n for n in module.body if isinstance(n, ast.Assign)
                  and len(n.targets) == 1 and isinstance(n.targets[0], ast.Name) and n.targets[0].id == name]
    if len(candidates) != 1:
        raise ValueError(f"missing or duplicated product-gate declaration {name}")
    node = candidates[0]
    for other in module.body:
        if other is node or isinstance(other, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            if getattr(other, "name", None) == name:
                raise ValueError(f"replaced product-gate declaration {name}")
            continue
        if any((isinstance(ref, ast.Name) and ref.id == name)
               or (isinstance(ref, ast.alias) and (ref.asname or ref.name) == name) for ref in ast.walk(other)):
            raise ValueError(f"replaced product-gate declaration {name}")
    return node.value


def _gated_ids(module, seen):
    node = _declaration(module, "_PLUGIN_PRODUCT_CHECK_IDS")
    if (not isinstance(node, ast.Call) or ast.unparse(node.func) != "frozenset"
            or len(node.args) != 1 or node.keywords or not isinstance(node.args[0], ast.Set)):
        raise ValueError("unsupported product-gate declaration")

    def read_id(value):
        if not isinstance(value, str) or not re.fullmatch(r"Check [0-9]+[a-z]?", value):
            raise ValueError(f"invalid product-gate id {value!r}")
        return value.removeprefix("Check ")

    declared = tuple(read_id(ast.literal_eval(item)) for item in node.args[0].elts)
    labels = ast.literal_eval(_declaration(module, "_PRODUCT_GATE_LABELS"))
    if (not isinstance(labels, dict) or len(declared) != len(set(declared))
            or set(declared) != seen or {read_id(label) for label in labels} != seen):
        raise ValueError("product-gate declarations do not match the executed reports")
    return declared


def bound_report_sources(engine_path, source, *, tree=None):
    """Read ordered report bodies from the inspected installation."""
    reports, _, _ = full_check_layout(engine_path, source, tree=tree)
    return reports


def _compares_governed_roots(function):
    if not _plain_function(function, "_host_plugin_roots_divergent", ""):
        return False
    body = _body(function)
    if (len(body) != 2 or ast.unparse(body[0]) != "import workflow_project_roots as paths"
            or not isinstance(body[1], ast.Try)):
        return False
    comparison = body[1]
    return (not comparison.orelse and not comparison.finalbody and len(comparison.handlers) == 1
            and ast.unparse(comparison.handlers[0]) == "except Exception:\n    return False"
            and [ast.unparse(step) for step in comparison.body] == [
                "host = os.path.normcase(os.path.abspath(os.fspath(paths.HOST_PROJECT_ROOT)))",
                "plugin = os.path.normcase(os.path.abspath(os.fspath(paths.PLUGIN_ROOT)))",
                "return host != plugin"])


def _split_report_bindings(engine_path, tree, installed):
    from cli_registration import inspect_cli_registration_tree

    facts = inspect_cli_registration_tree(engine_path, tree, "check-governance", "cmd_check_governance")
    if not all(facts.values()):
        raise ValueError(f"{engine_path}: check-governance is disconnected from the public dispatcher")
    command_path, _, command_tree = _report_module(engine_path, "governance_check_cli", installed)
    functions = _engine_functions(command_path, command_tree, {"cmd_check_governance", "_run_full_engine_checks"})
    if not _governance_command_consumes(functions.get("cmd_check_governance")):
        raise ValueError(f"{command_path}: check-governance no longer calls the full engine")
    selector_path, _, selector_tree = _report_module(engine_path, "workflow_report_selection", installed)
    selectors = _engine_functions(selector_path, selector_tree, {
        "_full_check_results", "_product_gate_active", "_host_plugin_roots_divergent", "_print_product_gate_skipped",
    })
    selector = selectors.get("_full_check_results")
    gate = selectors.get("_product_gate_active")
    if (not _plain_function(gate, "_product_gate_active", "args")
            or [ast.unparse(st) for st in _body(gate)] != [
                "if getattr(args, 'quick', False):\n    return False",
                "if not _host_plugin_roots_divergent():\n    return True",
                "return bool(getattr(args, 'product_gates', False))"]
            or not _compares_governed_roots(selectors.get("_host_plugin_roots_divergent"))):
        raise ValueError(f"{selector_path}: product-gate policy is missing")
    skipped = selectors.get("_print_product_gate_skipped")
    if (not _plain_function(skipped, "_print_product_gate_skipped", "check_id")
            or not _body(skipped) or ast.unparse(_body(skipped)[0]) != "label = _PRODUCT_GATE_LABELS.get(check_id, '')"):
        raise ValueError(f"{selector_path}: product-gate labels are disconnected from their renderer")
    return functions.get("_run_full_engine_checks"), selector_path, selector_tree, selector


def _report_uses_gate(selector_path, function, invocation, gate_bound, check_id):
    arguments = invocation.args
    parameters = function.args
    if (function.decorator_list or parameters.defaults or parameters.kwonlyargs or parameters.posonlyargs
            or parameters.vararg or parameters.kwarg or len(arguments) != len(parameters.args)
            or invocation.keywords):
        raise ValueError(f"{selector_path}: unbound report arguments for {function.name}")
    passed = [i for i, arg in enumerate(arguments)
              if isinstance(arg, ast.Name) and arg.id == "product_gate_active"]
    expected = [i for i, arg in enumerate(parameters.args) if arg.arg == "product_gate_active"]
    skipped = [i for i, arg in enumerate(parameters.args) if arg.arg == "_print_product_gate_skipped"]
    if (passed != expected or (expected and not gate_bound)
            or any(not isinstance(arguments[i], ast.Name) or arguments[i].id != "_print_product_gate_skipped" for i in skipped)):
        raise ValueError(f"{selector_path}: product-gate predicate is not bound at {function.name}")
    if not expected:
        return False
    body = _body(function)
    if body and ast.unparse(body[0]) == "issue_count = 0":
        body = body[1:]
    if not (body and isinstance(body[0], ast.If) and ast.unparse(body[0].test) == "product_gate_active()"
            and len(body[0].orelse) == 1):
        raise ValueError(f"{function.name}: missing active product-gate branch")
    inactive = body[0].orelse[0]
    marker = f"Check {check_id}"
    if skipped:
        describes_gate = ast.unparse(inactive) == f"_print_product_gate_skipped({marker!r})"
    else:
        describes_gate = (isinstance(inactive, ast.Expr) and isinstance(inactive.value, ast.Call)
                          and ast.unparse(inactive.value.func) == "print" and len(inactive.value.args) == 1
                          and isinstance(inactive.value.args[0], ast.Constant)
                          and f"[SKIP] {marker} " in str(inactive.value.args[0].value))
    if not describes_gate or not any(isinstance(node, ast.Call) and ast.unparse(node.func) != "print"
                                     for step in body[0].body for node in ast.walk(step)):
        raise ValueError(f"{function.name}: product-gate report branches are disconnected")
    return True


def full_check_layout(engine_path, source, *, tree=None):
    """Return reports, the module declaring their labels, and verified split-layout gates."""
    may_be_split = "build_runtime_parser" in source or "workflow_composition" in source
    if not may_be_split and "_full_check_results" not in source and "full_check_runner" not in source:
        return None, tree, None
    if tree is None:
        tree = parse_module_source(engine_path, source)
    split = any(isinstance(item, ast.ImportFrom) and (
        item.module == "workflow_composition" or item.module == "workflow_cli"
        and any(name.name == "build_runtime_parser" for name in item.names)) for item in tree.body)
    selector_path = engine_path
    selector_tree = tree
    imports = ["from full_check_runner import run_full_checks"]
    installed = None
    if split:
        from cli_startup_source import InstalledSources

        installed = InstalledSources(engine_path)
        entry, selector_path, selector_tree, selector = _split_report_bindings(engine_path, tree, installed)
        imports.append("from workflow_report_selection import _full_check_results")
    else:
        functions = _engine_functions(engine_path, tree, {"_full_check_results", "_run_full_engine_checks"})
        selector = functions.get("_full_check_results")
        entry = functions.get("_run_full_engine_checks")
    if selector is None:
        if split or (entry and any(isinstance(node, ast.ImportFrom) and node.module == "full_check_runner"
                                   for node in ast.walk(entry))):
            raise ValueError(f"{selector_path}: full-check selector is missing")
        return None, tree, None
    body = _body(entry) if entry else []
    if not (_plain_function(entry, "_run_full_engine_checks", "args") and len(body) == len(imports) + 1
            and sorted(ast.unparse(node) for node in body[:-1]) == sorted(imports)
            and ast.unparse(body[-1]) == "return run_full_checks(_full_check_results(args))"):
        raise ValueError(f"{engine_path}: full-check entry no longer consumes the report sequence")
    runner, _, runner_tree = _report_module(engine_path, "full_check_runner", installed)
    _verify_runner(runner, runner_tree)

    if not _plain_function(selector, "_full_check_results", "args"):
        raise ValueError(f"{engine_path}: unsupported full-check selector")
    if split:
        try:
            installed.module("workflow_report_selection")
        except (OSError, UnicodeError, SyntaxError, ValueError) as exc:
            raise ValueError(f"{selector_path}: unavailable full-check import: {exc}") from exc
    owners = {}
    providers = {}
    imported = set()
    owner_functions = {}
    reports = []
    seen = set()
    gated = set()
    gate_bound = False
    for node in _body(selector):
        if isinstance(node, ast.Import):
            for alias in node.names:
                binding = alias.asname or alias.name
                if binding in imported or binding in ("product_gate_active", "_product_gate_active", "args"):
                    raise ValueError(f"{selector_path}: conflicting selector import {binding}")
                imported.add(binding)
                if split and not installed.available(alias.name):
                    raise ValueError(f"{selector_path}: unavailable selector dependency {alias.name}")
                if re.fullmatch(r"health_[a-z_]+_sections", alias.name):
                    owners[binding] = alias.name
                elif split and alias.name.isidentifier():
                    providers[binding] = alias.name
                else:
                    raise ValueError(f"{selector_path}: unknown selector dependency {alias.name}")
            continue
        if (_plain_function(node, "product_gate_active", "")
                and [ast.unparse(st) for st in _body(node)] == ["return _product_gate_active(args)"]):
            if gate_bound:
                raise ValueError(f"{selector_path}: duplicate product-gate predicate")
            gate_bound = True
            continue
        if not (isinstance(node, ast.Expr) and isinstance(node.value, ast.Yield)
                and isinstance(node.value.value, ast.Call)
                and isinstance(node.value.value.func, ast.Attribute)
                and isinstance(node.value.value.func.value, ast.Name)):
            raise ValueError(f"{selector_path}:{node.lineno}: unsupported full-check sequence statement")
        target = node.value.value.func
        owner = owners.get(target.value.id)
        match = re.fullmatch(r"section_([0-9]+[a-z]?)_[a-z0-9_]+", target.attr)
        if not owner or not match:
            raise ValueError(f"{engine_path}: unresolved report call {ast.unparse(target)}")
        if owner not in owner_functions:
            path, module, owner_tree = _report_module(engine_path, owner, installed)
            lines = module.splitlines(keepends=True)
            names = {fn.name for fn in owner_tree.body if isinstance(fn, ast.FunctionDef)
                     and fn.name.startswith("section_")}
            definitions = _engine_functions(path, owner_tree, names)
            owner_functions[owner] = {name: (fn, "".join(lines[fn.lineno - 1:fn.end_lineno]))
                                      for name, fn in definitions.items()}
        if target.attr not in owner_functions[owner]:
            raise ValueError(f"{engine_path}: missing report {owner}.{target.attr}")
        check_id = match.group(1)
        if check_id in seen:
            raise ValueError(f"{engine_path}: duplicate check id {check_id}")
        seen.add(check_id)
        function, report = owner_functions[owner][target.attr]
        if split:
            for argument in node.value.value.args:
                if (isinstance(argument, ast.Attribute) and isinstance(argument.value, ast.Name)
                        and argument.value.id in providers):
                    installed.member(providers[argument.value.id], argument.attr)
                elif isinstance(argument, ast.Name) and argument.id not in {"args", "product_gate_active"}:
                    installed.member("workflow_report_selection", argument.id)
        if split and _report_uses_gate(selector_path, function, node.value.value, gate_bound, check_id):
            gated.add(check_id)
        reports.append((check_id, report))
    return tuple(reports), selector_tree, _gated_ids(selector_tree, gated) if split else None
