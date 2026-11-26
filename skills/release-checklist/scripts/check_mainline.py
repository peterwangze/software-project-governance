"""Verify the release checkout's local integration branch against the live remote."""

import argparse
import os
import subprocess
import sys


def git(*args):
    return subprocess.check_output(
        ["git", *args], text=True, encoding="utf-8", errors="replace",
        env={**os.environ, "GIT_TERMINAL_PROMPT": "0"}, timeout=30,
    ).strip()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("branch", help="Local and remote integration branch, e.g. master")
    parser.add_argument("--remote", default="origin", help="Configured Git remote (default: origin)")
    args = parser.parse_args()
    ref = f"refs/heads/{args.branch}"
    try:
        if args.remote not in git("remote").splitlines():
            sys.exit(f"Remote {args.remote!r} is not configured")
        local = git("show-ref", "--verify", "--hash", ref)
        advertised = git("ls-remote", "--exit-code", "--refs", "--", args.remote, ref)
    except (OSError, subprocess.SubprocessError) as exc:
        sys.exit(f"Unable to verify {ref} against {args.remote}: {exc}")

    for line in advertised.splitlines():
        oid, _, name = line.partition("\t")
        if name == ref:
            print(f"local {ref} {local}\n{args.remote} {ref} {oid}")
            return 0 if local == oid else 1
    sys.exit(f"{args.remote} did not advertise the exact ref {ref}")


if __name__ == "__main__":
    sys.exit(main())
