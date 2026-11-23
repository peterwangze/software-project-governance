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


def _engine_functions(path, tree):
    names = {"_full_check_results", "_run_full_engine_checks"}
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


def _plain_function(node, name, parameter):
    return (isinstance(node, ast.FunctionDef) and node.name == name
            and not node.decorator_list and node.returns is None
            and not getattr(node, "type_params", ()) and ast.unparse(node.args) == parameter)


def _verify_runner(path):
    """Prove this installed runner consumes every yielded count and returns their sum."""
    _, module = _module_source(path)
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


def bound_report_sources(engine_path, source, *, tree=None):
    """Return (id, report source) in execution order, or None for the legacy engine."""
    if "_full_check_results" not in source and "full_check_runner" not in source:
        return None  # The historical engine census only needs its section markers.
    if tree is None:
        tree = parse_module_source(engine_path, source)
    functions = _engine_functions(engine_path, tree)
    entry = functions.get("_run_full_engine_checks")
    selector = functions.get("_full_check_results")
    if selector is None:
        if entry and any(isinstance(node, ast.ImportFrom) and node.module == "full_check_runner"
                         for node in ast.walk(entry)):
            raise ValueError(f"{engine_path}: full-check selector is missing")
        return None
    body = _body(entry) if entry else []
    if not (_plain_function(entry, "_run_full_engine_checks", "args")
            and len(body) == 2 and isinstance(body[0], ast.ImportFrom)
            and body[0].level == 0 and body[0].module == "full_check_runner"
            and [(alias.name, alias.asname) for alias in body[0].names] == [("run_full_checks", None)]
            and isinstance(body[1], ast.Return)
            and ast.unparse(body[1].value) == "run_full_checks(_full_check_results(args))"):
        raise ValueError(f"{engine_path}: full-check entry no longer consumes the report sequence")

    _verify_runner(engine_path.with_name("full_check_runner.py"))

    if not _plain_function(selector, "_full_check_results", "args"):
        raise ValueError(f"{engine_path}: unsupported full-check selector")
    owners = {}
    owner_functions = {}
    reports = []
    seen = set()
    for node in _body(selector):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if not re.fullmatch(r"health_[a-z_]+_sections", alias.name):
                    raise ValueError(f"{engine_path}: unexpected report owner {alias.name}")
                binding = alias.asname or alias.name
                if binding in owners or binding == "product_gate_active":
                    raise ValueError(f"{engine_path}: conflicting report owner {binding}")
                owners[binding] = alias.name
            continue
        if (_plain_function(node, "product_gate_active", "")
                and [ast.unparse(st) for st in _body(node)] == ["return _product_gate_active(args)"]):
            continue
        if not (isinstance(node, ast.Expr) and isinstance(node.value, ast.Yield)
                and isinstance(node.value.value, ast.Call)
                and isinstance(node.value.value.func, ast.Attribute)
                and isinstance(node.value.value.func.value, ast.Name)):
            raise ValueError(f"{engine_path}:{node.lineno}: unsupported full-check sequence statement")
        target = node.value.value.func
        owner = owners.get(target.value.id)
        match = re.fullmatch(r"section_([0-9]+[a-z]?)_[a-z0-9_]+", target.attr)
        if not owner or not match:
            raise ValueError(f"{engine_path}: unresolved report call {ast.unparse(target)}")
        if owner not in owner_functions:
            path = engine_path.with_name(owner + ".py")
            module, owner_tree = _module_source(path)
            lines = module.splitlines(keepends=True)
            owner_functions[owner] = {
                fn.name: "".join(lines[fn.lineno - 1:fn.end_lineno])
                for fn in owner_tree.body if isinstance(fn, ast.FunctionDef)
            }
        if target.attr not in owner_functions[owner]:
            raise ValueError(f"{engine_path}: missing report {owner}.{target.attr}")
        check_id = match.group(1)
        if check_id in seen:
            raise ValueError(f"{engine_path}: duplicate check id {check_id}")
        seen.add(check_id)
        reports.append((check_id, owner_functions[owner][target.attr]))
    return tuple(reports)
