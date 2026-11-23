"""Inspect and manage the optional local web console."""

import os
import shutil
import subprocess
import sys
import time


def _web_console_url(host="127.0.0.1", port=5173):
    return f"http://{host}:{port}/"


def _resolve_web_install_timeout(raw, *, default_seconds, positive_timeout):
    """FIX-238.4: resolve the web-console npm install timeout.

    SPG_WEB_INSTALL_TIMEOUT (positive integer seconds, default 120s) with
    invalid values falling back to the default (FIX-234 precedent).
    """
    return positive_timeout(raw, default_seconds)


def _web_console_is_live(url, timeout=1.5, *, web_console_probe):
    return web_console_probe(url, timeout=timeout)["state"] == "running"


def _web_console_probe(url, timeout=1.5, *, open_url):
    try:
        with open_url(url, timeout=timeout) as response:
            body = response.read(65536).decode("utf-8", errors="replace")
            if 'name="spg-web-console"' in body and "software-project-governance" in body:
                return {"state": "running", "status": response.status}
            return {"state": "occupied", "status": response.status}
    except Exception as exc:
        return {"state": "not_running", "error": str(exc)}


def _web_console_paths(*, product_root):
    web_dir = product_root / "web"
    return {
        "web_dir": web_dir,
        "package_json": web_dir / "package.json",
        "node_modules": web_dir / "node_modules",
        "log": web_dir / "web-dev.log",
        "pid": web_dir / ".spg-web-console.pid",
    }


def _write_web_console_process(paths, process):
    try:
        paths["pid"].write_text(str(process.pid), encoding="utf-8")
    except OSError:
        pass


def cmd_web_console(
    args, *, host_root, product_root, install_timeout, display_path,
    web_console_is_live, web_console_paths, web_console_probe,
    web_console_url, write_web_console_process, open_browser, now,
):
    """Expose the optional local Web console through the primary CLI/client path."""
    paths = web_console_paths()
    url = web_console_url(args.host, args.port)
    if getattr(args, "governance_entry", False):
        args.start = True

    print("Software Project Governance Web Console")
    print("Role: optional local companion dashboard")
    print("Primary interface remains: CLI / agent client")
    print(f"URL: {url}")
    print(f"Web directory: {display_path(paths['web_dir'])}")
    probe = web_console_probe(url)

    if args.summary_link and args.start:
        print("\nStatus: blocked")
        print("Reason: --summary-link is read-only and cannot be combined with a start path.")
        print("Boundary: summaries may report Web console status, while manual /governance uses --governance-entry to start or reuse it.")
        if args.fail_on_issues:
            sys.exit(1)
        return

    if not paths["package_json"].is_file():
        print("\nStatus: unavailable")
        print("Reason: web/package.json is missing in this checkout.")
        print("Boundary: this command does not replace /governance or run agent tasks.")
        if args.fail_on_issues:
            sys.exit(1)
        return

    if args.summary_link:
        if probe["state"] == "running":
            print(f"\nWeb console: {url} (optional local companion dashboard)")
        elif probe["state"] == "occupied":
            print(f"\nWeb console: unavailable at {url} (port is occupied by a non-SPG service).")
            print("Manual start command: python skills/software-project-governance/infra/verify_workflow.py web-console --start --port <free-port>")
            if args.fail_on_issues:
                sys.exit(1)
        else:
            print("\nWeb console: not running.")
            print("Manual start command: python skills/software-project-governance/infra/verify_workflow.py web-console --start")
        print("Boundary: summary link only; no Web service was started.")
        return

    if args.status and not args.start:
        if probe["state"] == "occupied":
            print("\nStatus: port occupied by a non-SPG service")
            print("Action: choose another port with --port, or stop the service using this port.")
            if args.fail_on_issues:
                sys.exit(1)
            return
        print("\nStatus:", "running" if probe["state"] == "running" else "not running")
        print("\nManual start command:")
        print(
            "python skills/software-project-governance/infra/verify_workflow.py "
            "web-console --start"
        )
        print("\nFirst run with dependency install:")
        print(
            "python skills/software-project-governance/infra/verify_workflow.py "
            "web-console --start --install"
        )
        print("\n/governance entry command:")
        print(
            "python skills/software-project-governance/infra/verify_workflow.py "
            "web-console --governance-entry"
        )
        print("\nBoundary: manual /governance starts or reuses the Web console for follow-up UI interaction; task/session summaries remain read-only with --summary-link.")
        return

    if not args.start:
        if probe["state"] == "occupied":
            print("\nStatus: port occupied by a non-SPG service")
            print("Use --port to select another local port.")
            if args.fail_on_issues:
                sys.exit(1)
            return
        print("\nStatus:", "running" if probe["state"] == "running" else "not running")
        print("Manual start command: python skills/software-project-governance/infra/verify_workflow.py web-console --start")
        return

    if probe["state"] == "occupied":
        print("\nStatus: blocked")
        print("Reason: the target port is serving a non-SPG page.")
        print("Action: use --port to select another local port, or stop the other service.")
        if args.fail_on_issues:
            sys.exit(1)
        return

    if probe["state"] == "running":
        print("\nStatus: already running")
        if getattr(args, "governance_entry", False):
            print("Entry: manual /governance reused the running Web console.")
        if args.open:
            open_browser(url)
        return

    npm = shutil.which("npm")
    if not npm:
        print("\nStatus: blocked")
        print("Reason: npm was not found on PATH.")
        if args.fail_on_issues:
            sys.exit(1)
        return

    if not paths["node_modules"].is_dir():
        if not args.install:
            print("\nStatus: blocked")
            print("Reason: web/node_modules is missing.")
            print("First run command:")
            print(
                "python skills/software-project-governance/infra/verify_workflow.py "
                "web-console --start --install"
            )
            if getattr(args, "governance_entry", False):
                print("Governance entry: default start attempted; dependency install still requires explicit --install.")
            if args.fail_on_issues:
                sys.exit(1)
            return
        print("\nInstalling web dependencies with npm install...")
        timeout = install_timeout()
        try:
            install_result = subprocess.run(
                [npm, "install"], cwd=paths["web_dir"], timeout=timeout
            )
        except subprocess.TimeoutExpired:
            print("Status: blocked")
            print(
                f"Reason: npm install timed out after {timeout}s "
                f"(SPG_WEB_INSTALL_TIMEOUT); raise the value or inspect the npm log."
            )
            if args.fail_on_issues:
                sys.exit(124)
            return
        if install_result.returncode != 0:
            print("Status: blocked")
            print(f"Reason: npm install exited {install_result.returncode}.")
            if args.fail_on_issues:
                sys.exit(install_result.returncode)
            return

    api_server_script = product_root() / "web" / "server.py"
    api_port = args.port + 1 if args.port != 5173 else 5174
    api_started = False
    if api_server_script.is_file():
        api_log = paths["web_dir"] / ".api-server.log"
        api_log_handle = api_log.open("a", encoding="utf-8")
        api_log_handle.write(
            f"\n--- api-server start {now().isoformat(timespec='seconds')} ---\n"
        )
        api_log_handle.flush()
        api_popen_kwargs = {
            "cwd": str(product_root()),
            "stdout": api_log_handle,
            "stderr": subprocess.STDOUT,
            "stdin": subprocess.DEVNULL,
        }
        if os.name == "nt":
            api_popen_kwargs["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP
        else:
            api_popen_kwargs["start_new_session"] = True
        try:
            api_process = subprocess.Popen(
                [sys.executable, str(api_server_script), "--port", str(api_port), "--project-root", str(host_root())],
                **api_popen_kwargs,
            )
            api_started = True
            (paths["web_dir"] / ".api-server.pid").write_text(str(api_process.pid), encoding="utf-8")
        except Exception as exc_api:  # pragma: no cover - defensive
            print(f"\nNote: local API server could not start ({exc_api}); the dashboard will run without live data.")
        finally:
            api_log_handle.close()
    else:
        print("\nNote: web/server.py not found; the dashboard will run without live data.")

    command = [
        npm,
        "run",
        "dev",
        "--",
        "--host",
        args.host,
        "--port",
        str(args.port),
    ]

    if args.foreground:
        print("\nStatus: starting in foreground")
        print("Stop with Ctrl+C.")
        os.execvpe(command[0], command, os.environ)

    log_handle = paths["log"].open("a", encoding="utf-8")
    log_handle.write(f"\n--- web-console start {now().isoformat(timespec='seconds')} ---\n")
    log_handle.flush()

    popen_kwargs = {
        "cwd": paths["web_dir"],
        "stdout": log_handle,
        "stderr": subprocess.STDOUT,
        "stdin": subprocess.DEVNULL,
    }
    if os.name == "nt":
        popen_kwargs["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP
    else:
        popen_kwargs["start_new_session"] = True

    try:
        process = subprocess.Popen(command, **popen_kwargs)
    finally:
        log_handle.close()
    write_web_console_process(paths, process)

    for _ in range(30):
        if web_console_is_live(url):
            print("\nStatus: running")
            print(f"PID: {process.pid}")
            print(f"Log: {display_path(paths['log'])}")
            if api_started:
                print(f"Local API server: http://127.0.0.1:{api_port}/api/governance (live governance data)")
                print(f"API PID: {api_process.pid} (stop: taskkill /PID {api_process.pid} /F on Windows)")
            if args.open:
                open_browser(url)
            return
        time.sleep(0.5)

    print("\nStatus: starting")
    print(f"PID: {process.pid}")
    print(f"Log: {display_path(paths['log'])}")
    print("The server did not respond within 15 seconds; check the log above.")
    if args.fail_on_issues:
        sys.exit(1)
