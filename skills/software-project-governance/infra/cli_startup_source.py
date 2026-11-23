"""Static dependencies of the shipped split CLI. Inspected files are never imported."""
import ast
import builtins
import sys
from functools import lru_cache
from importlib.util import decode_source


class _Source:
    """Only modules inspected in detail retain their syntax tree between calls."""

    def __init__(self):
        self.detail = None
        self.interface = None


@lru_cache(maxsize=128)
def _source(text):
    """Reuse facts only when freshly read input yields identical Python text."""
    return _Source()


def _source_interface(tree):
    # ast.parse accepts structurally invalid programs such as a module-level return.
    compile(tree, "<inspected source>", "exec", dont_inherit=True)
    body = tree.body
    imports = []
    exports = {}
    for node in body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            exports[node.name] = type(node).__name__
        elif isinstance(node, (ast.Import, ast.ImportFrom)):
            module = (node.module or "") if isinstance(node, ast.ImportFrom) else None
            level = getattr(node, "level", 0)
            for item in node.names:
                bound = item.asname or item.name.split(".")[0]
                exports[bound] = "import"
                imports.append((module, level, item.name))
        elif isinstance(node, (ast.Assign, ast.AnnAssign, ast.Delete)):
            targets = node.targets if hasattr(node, "targets") else [node.target]
            for target in targets:
                for symbol in ast.walk(target):
                    if isinstance(symbol, ast.Name) and isinstance(symbol.ctx, ast.Store):
                        exports[symbol.id] = "value"
                    elif isinstance(symbol, ast.Name) and isinstance(symbol.ctx, ast.Del):
                        exports.pop(symbol.id, None)
    return imports, exports


class InstalledSources:
    """Resolve unconditional Python imports from one installation's infra directory."""

    def __init__(self, entry, *, share_syntax=False):
        self.root = entry.parent
        self.modules = {}
        self._locations = {}
        self._contents = {}
        self._trees = {} if share_syntax else None

    def read(self, path):
        """Read a sibling once in this observation. A new observation starts empty."""
        key = str(path)
        if key not in self._contents:
            self._contents[key] = path.read_bytes()
        return self._contents[key]

    def _tree(self, text, *, keep=False):
        source = _source(text)
        tree = source.detail
        if tree is None and self._trees is not None:
            tree = self._trees.get(text)
        if tree is None:
            tree = ast.parse(text)
            if self._trees is not None:
                self._trees[text] = tree
        if keep:
            source.detail = tree
        return tree

    def interface(self, raw):
        text = decode_source(raw)
        source = _source(text)
        if source.interface is None:
            source.interface = _source_interface(self._tree(text))
        return source.interface

    def _location(self, name):
        """A regular package wins over a module, which wins over a namespace."""
        if name in self._locations:
            return self._locations[name]
        if not name or not all(part.isidentifier() for part in name.split(".")):
            raise ValueError(f"invalid local module {name!r}")
        directory = self.root.joinpath(*name.split("."))
        parent = name.rpartition(".")[0]
        if parent:
            parent_source = self._location(parent)
            if parent_source is not None and parent_source != directory.parent / "__init__.py":
                raise FileNotFoundError(f"{parent} is not a package")
        package = directory / "__init__.py"
        if package.is_file():
            source = package
        else:
            source = directory.with_suffix(".py")
            try:
                self.read(source)
            except FileNotFoundError:
                if not directory.is_dir():
                    raise
                source = None
        self._locations[name] = source
        return source

    def syntax(self, name):
        """Return the selected source path, decoded Python text and matching AST."""
        path = self._location(name)
        if path is None:
            raise FileNotFoundError(f"namespace package {name} has no source body")
        text = decode_source(self.read(path))
        return path, text, self._tree(text, keep=True)

    def missing(self, name):
        try:
            self._location(name)
        except FileNotFoundError:
            return True
        return False

    def module(self, name):
        if name in self.modules:
            return self.modules[name]
        source = self._location(name)
        imports, exports = self.interface(self.read(source)) if source is not None else ((), {})
        # Python places a module in the import cache before resolving its children.
        self.modules[name] = exports
        try:
            package = source is None or source.parent == self.root.joinpath(*name.split("."))
            self._dependencies(name, package, imports)
        except (OSError, SyntaxError, UnicodeError, ValueError):
            self.modules.pop(name)
            raise
        return exports

    def _dependencies(self, name, is_package, imports):
        if "." in name:
            self.module(name.rpartition(".")[0])
        for owner, level, member in imports:
            if level:
                prefix = (name if is_package else name.rpartition(".")[0]).split(".")
                if level > len(prefix) or not all(prefix):
                    raise ValueError(f"relative import outside {name}")
                owner = ".".join([*prefix[:len(prefix) - level + 1], *([owner] if owner else [])])
            self.imported(owner, member)

    def available(self, name):
        try:
            self.module(name)
        except (OSError, SyntaxError, UnicodeError, ValueError):
            return False
        return True

    def imported(self, owner, member):
        target = member if owner is None else owner
        if target.split(".")[0] in sys.stdlib_module_names:
            return
        exports = self.module(target)
        if owner is not None and member not in exports:
            # A package may export a submodule with no declaration in __init__.py.
            self.module(f"{target}.{member}")

    def member(self, owner, name, *, called=False):
        kind = self.module(owner).get(name)
        if kind is None or called and kind not in {"FunctionDef", "ClassDef", "import"}:
            raise ValueError(f"unavailable {'callable' if called else 'member'} {owner}.{name}")


def _immediate_reads(node):
    """Exclude deferred callback bodies; their modules belong to their consuming command."""
    if isinstance(node, (ast.Lambda, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
        return
    yield node
    for child in ast.iter_child_nodes(node):
        yield from _immediate_reads(child)


def _require_imports(sources, statements):
    for statement in statements:
        if isinstance(statement, ast.Import):
            for alias in statement.names:
                sources.imported(None, alias.name)
        elif isinstance(statement, ast.ImportFrom):
            if statement.level or not statement.module:
                raise ValueError("unsupported relative import in the public CLI")
            for alias in statement.names:
                sources.imported(statement.module, alias.name)


def _imported_names(statements):
    return {alias.asname or alias.name: (node.module, alias.name)
            for node in statements if isinstance(node, ast.ImportFrom) and not node.level
            and node.module and node.module.split(".")[0] not in sys.stdlib_module_names
            for alias in node.names}


def _require_imported_calls(sources, statement, imports, allowed):
    locals_in_statement = {n.id for n in _immediate_reads(statement)
                           if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Store)}
    for node in _immediate_reads(statement):
        if (isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load) and node.id not in allowed
                and node.id not in locals_in_statement and not hasattr(builtins, node.id)):
            raise ValueError(f"unbound startup name {node.id}")
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id in imports:
            sources.member(*imports[node.func.id], called=True)
        if (isinstance(node, ast.Assign) and isinstance(node.value, ast.Name) and node.value.id in imports
                and any(isinstance(t, ast.Attribute) and t.attr == "__class__" for t in node.targets)):
            owner, name = imports[node.value.id]
            if sources.module(owner).get(name) != "ClassDef":
                raise ValueError(f"unavailable module class {owner}.{name}")


@lru_cache(maxsize=8)
def _public_helpers(tree):
    body = tree.body
    modules = {item.asname or item.name: item.name for node in body if isinstance(node, ast.Import)
               for item in node.names if item.name.split(".")[0] not in sys.stdlib_module_names}
    return {node.name: node for node in body if isinstance(node, ast.FunctionDef)}, modules


def _require_public_helpers(sources, engine, imports):
    """Follow shell startup calls (including __dir__) but leave exported getters deferred."""
    local = {n.name: n for n in engine if isinstance(n, ast.FunctionDef)}
    pending = list(engine)
    reached = set()
    _, _, public = sources.syntax("workflow_public_api")
    functions, modules = _public_helpers(public)
    while pending:
        for node in _immediate_reads(pending.pop()):
            if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Name):
                continue
            name = node.func.id
            if name in reached:
                continue
            reached.add(name)
            if name in local:
                pending.extend(local[name].body)
            elif name in imports and imports[name][0] == "workflow_public_api":
                function = functions.get(imports[name][1])
                if function is None:
                    raise ValueError(f"unavailable public startup function {name}")
                _require_imports(sources, function.body)
                called_imports = _imported_names(function.body)
                for statement in function.body:
                    for read in _immediate_reads(statement):
                        if isinstance(read, ast.Call) and isinstance(read.func, ast.Name) and read.func.id in called_imports:
                            sources.member(*called_imports[read.func.id], called=True)
                        if (isinstance(read, ast.Attribute) and isinstance(read.value, ast.Name)
                                and read.value.id in modules and isinstance(read.ctx, ast.Load)):
                            sources.member(modules[read.value.id], read.attr)


def _require_install_reads(sources, composition, install):
    imports = _imported_names(composition)
    bound = set(sources.module("workflow_composition"))
    families = {}
    for node in composition:
        if (isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name)
                and isinstance(node.value, ast.Call) and isinstance(node.value.func, ast.Name)
                and imports.get(node.value.func.id) == ("workflow_public_api", "DeferredFamily")
                and len(node.value.args) == 1 and isinstance(node.value.args[0], ast.Constant)):
            families[node.targets[0].id] = node.value.args[0].value
    active = []
    for statement in install:
        # Guarded imports have command-specific fallbacks. A loaded optional
        # module must still have the setter used by its active else arm.
        if isinstance(statement, ast.Try):
            if len(statement.body) != 1 or len(statement.handlers) != 1 or statement.finalbody:
                raise ValueError("unsupported guarded installation")
            required = statement.body[0]
            catches = ast.unparse(statement.handlers[0].type)
            try:
                _require_imports(sources, [required])
            except (FileNotFoundError, SyntaxError, UnicodeError, ValueError):
                if catches == "(ImportError, SyntaxError)":
                    continue
                if (isinstance(required, ast.ImportFrom) and catches == "ModuleNotFoundError"
                        and sources.missing(required.module)):
                    continue
                raise
            imports.update(_imported_names(statement.body))
            bound.update(_imported_names(statement.body))
            active.extend(statement.orelse)
        else:
            active.append(statement)
    for statement in active:
        _require_imported_calls(sources, statement, imports, bound)
        for node in _immediate_reads(statement):
            if (isinstance(node, ast.Attribute) and isinstance(node.ctx, ast.Load)
                    and isinstance(node.value, ast.Name) and node.value.id in families):
                sources.member(families[node.value.id], node.attr)
            if (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
                    and isinstance(node.func.value, ast.Name) and node.func.value.id in families):
                sources.member(families[node.func.value.id], node.func.attr, called=True)


def split_startup_sources(sources, engine, installation):
    """Verify the imports and immediate provider reads before normal command dispatch."""
    try:
        _require_imports(sources, engine)
        imports = _imported_names(engine)
        # The caller has already read the shell. Do not reopen it during this proof.
        bound = {node.name for node in engine if isinstance(node, (ast.FunctionDef, ast.ClassDef))}
        bound.update(item.asname or item.name.split(".")[0] for node in engine
                     if isinstance(node, (ast.Import, ast.ImportFrom)) for item in node.names)
        bound.update({"__file__", "__name__"})
        for statement in engine:
            _require_imported_calls(sources, statement, imports, bound)
        _require_public_helpers(sources, engine, imports)
        if installation is None:
            return None
        composition, install, _ = installation
        _require_install_reads(sources, composition, install)
    except (OSError, UnicodeError, SyntaxError, ValueError):
        return None
    return sources
