from pathlib import Path
import json

ROOT = Path(__file__).resolve().parents[2]
MANIFEST_PATH = ROOT / "adapters/codex/adapter-manifest.json"


def main():
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    print("== Codex Adapter Launcher ==")
    print(f"workflow: {manifest['workflow_id']}")
    print(f"entry_type: {manifest['entry_type']}")
    print(f"support_status: {manifest['support_status']}")
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
    print("runtime_e2e:")
    runtime_e2e = manifest.get("runtime_e2e")
    if not isinstance(runtime_e2e, dict) or not runtime_e2e:
        raise ValueError("adapter manifest must define a non-empty runtime_e2e object")
    print(f" - e2e_level: {runtime_e2e['e2e_level']}")
    print(f" - command: {runtime_e2e['command']}")
    print(f" - version_command: {runtime_e2e['version_command']}")
    for key in ("target_cwd_e2e", "agent_runtime_e2e"):
        block = runtime_e2e.get(key, {})
        print(f" - {key}.status: {block.get('status')}")
        if block.get("command"):
            print(f" - {key}.command: {block['command']}")
        if block.get("blocked_reason"):
            print(f" - {key}.blocked_reason: {block['blocked_reason']}")
    print(f" - full_e2e_verified: {runtime_e2e.get('full_e2e_verified')}")
    print("validation:")
    print(f" - command: {manifest['validation']['command']}")


if __name__ == "__main__":
    main()
