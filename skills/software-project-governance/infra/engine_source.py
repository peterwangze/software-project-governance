"""Share a read-only entry AST across the live observers in one quick command."""
import ast
import os
from contextlib import contextmanager
from contextvars import ContextVar


# None outside a command, an empty tuple before its first observation.
_last_engine = ContextVar("last_observed_engine_source", default=None)


@contextmanager
def engine_source_scope():
    token = _last_engine.set(())
    try:
        yield
    finally:
        _last_engine.reset(token)


def parse_engine_source(path, source):
    """Reuse only an identical target and freshly read text. Consumers must not mutate the AST."""
    previous = _last_engine.get()
    if previous is not None:
        resolved_path = os.path.realpath(path)
        if previous and previous[0] == resolved_path and previous[1] == source:
            return previous[2]
    tree = ast.parse(source, filename=str(path))
    if previous is not None:
        _last_engine.set((resolved_path, source, tree))
    return tree
