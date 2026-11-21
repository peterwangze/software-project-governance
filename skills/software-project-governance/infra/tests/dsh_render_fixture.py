"""Deterministic disk host for the directory installer and its failure tests."""
import os
from pathlib import Path
import tempfile
from unittest.mock import patch


def bind_render_host(cls):
    """Install a class-scoped synthetic DSH base; never depend on the user host."""
    host_tmp = tempfile.TemporaryDirectory(prefix="dsh-render-host-")
    cls.addClassCleanup(host_tmp.cleanup)
    modules = Path(host_tmp.name) / "node_modules"
    anchor = modules / "@deepseek-ai/dsh/package.json"
    anchor.parent.mkdir(parents=True)
    anchor.write_text('{"version":"1.2.3"}', encoding="utf-8")
    patch_file = modules / "@deepseek-ai/dsh-web-app/presets/standard.patch.yml"
    patch_file.parent.mkdir(parents=True)
    patch_file.write_text(
        "- insert:\n    - id: preset-standard\n      name: '@deepseek-ai/dsh-agent-preset'\n"
        "      config:\n        id: standard\n        plugins:\n"
        "          - id: persona\n            name: '@deepseek-ai/dsh-persona'\n"
        "            config:\n              prefix: Host identity.\n"
        "          - id: host-fixture-tool\n            name: host-fixture-tool\n"
        "          - id: skill-filesystem\n            name: '@deepseek-ai/dsh-skill-filesystem'\n",
        encoding="utf-8")
    cls.host_patch = patch_file
    cls.plane_env = {"DSH_INSTALL_DIR": str(modules)}
    env = patch.dict(os.environ, cls.plane_env)
    env.start()
    cls.addClassCleanup(env.stop)
