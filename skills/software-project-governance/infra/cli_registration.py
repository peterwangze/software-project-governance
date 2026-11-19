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


def inspect_cli_registration(path: Path, key: str, handler: str) -> dict:
    """Observe the target's parser and actual call to its selected handler."""
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    functions = {node.name: node for node in tree.body if isinstance(node, ast.FunctionDef)}
    main = functions.get("main")
    statements = main.body if main else []
    parser_body = statements
    for node in statements:
        if isinstance(node, ast.Assign) and isinstance(node.value, ast.Call):
            if ast.unparse(node.value.func) == "_build_cli_parser":
                builder = functions.get("_build_cli_parser")
                parser_body = builder.body if builder else ()
                break
    has_parser = any(
        isinstance(node, (ast.Assign, ast.Expr)) and isinstance(node.value, ast.Call)
        and ast.unparse(node.value.func) == "subparsers.add_parser" and node.value.args
        and isinstance(node.value.args[0], ast.Constant) and node.value.args[0].value == key
        for node in parser_body
    )
    return {"main": main is not None, "handler": handler in functions,
            "argparse": has_parser, "dispatch": _has_dispatch(path, statements, key, handler)}
