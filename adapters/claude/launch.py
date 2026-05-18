from pathlib import Path
import json

ROOT = Path(__file__).resolve().parents[2]
MANIFEST_PATH = ROOT / "adapters/claude/adapter-manifest.json"


def main():
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    print("== Claude Adapter Launcher ==")
    print(f"workflow: {manifest['workflow_id']}")
    print(f"entry_type: {manifest['entry_type']}")
    print("trigger:")
    for item in manifest["trigger"]:
        print(f" - {item}")
    print("read_order:")
    for index, item in enumerate(manifest["inputs"], start=1):
        print(f" {index}. {item}")
    print("outputs:")
    for item in manifest["outputs"]:
        print(f" - {item}")
    print("gate_behavior:")
    print(f" - on_fail: {manifest['gate_behavior']['on_fail']}")
    print(f" - required_action: {manifest['gate_behavior']['required_action']}")
    print("native_entry:")
    native_entry = manifest.get("native_entry")
    if not isinstance(native_entry, dict) or not native_entry:
        raise ValueError("adapter manifest must define a non-empty native_entry object")
    for key in sorted(native_entry):
        print(f" - {key}: {native_entry[key]}")
    print("validation:")
    print(f" - command: {manifest['validation']['command']}")


if __name__ == "__main__":
    main()
