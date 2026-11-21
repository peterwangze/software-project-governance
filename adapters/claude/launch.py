from pathlib import Path
from runpy import run_path

ROOT = Path(__file__).resolve().parents[2]
MANIFEST_PATH = ROOT / "adapters/claude/adapter-manifest.json"


def main():
    # Resolve the bundled renderer by file even under python -I and a host-project cwd.
    report = run_path(str(ROOT / "adapters/manifest_report.py"))
    report["print_manifest_report"](MANIFEST_PATH, "Claude")


if __name__ == "__main__":
    main()
