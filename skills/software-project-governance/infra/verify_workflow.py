"""Governance CLI startup, command dispatch and the historical Python import surface."""
import sys

from resolve_entry import (
    _dispatch_bootstrap_if_selected,
    extract_project_root_arg as _extract_project_root_arg,
    validate_project_root as _validate_project_root,
)


if __name__ == "__main__" and "governance-bootstrap" in sys.argv[1:]:
    _dispatch_bootstrap_if_selected(sys.argv[1:])

if __name__ == "__main__":
    sys.modules.setdefault("verify_workflow", sys.modules[__name__])

import workflow_project_roots as _paths
from workflow_project_roots import _apply_project_root_override
from workflow_cli import build_runtime_parser as _build_cli_parser, main
from workflow_composition import ensure_installed as _install
from workflow_public_api import (
    PublicModule as _WorkflowModule,
    bind_host_projection as _bind_host_projection,
    names as _public_names,
    read_public as __getattr__,
)


def __dir__():
    return sorted(set(globals()) | _public_names())


if __name__ in ("__main__", "verify_workflow"):
    _install()
if __name__ in sys.modules and sys.modules[__name__].__dict__ is globals():
    sys.modules[__name__].__class__ = _WorkflowModule
    _bind_host_projection(sys.modules[__name__])
__all__ = sorted(name for name in __dir__() if not name.startswith("_"))


if __name__ == "__main__":
    sys.exit(main())
