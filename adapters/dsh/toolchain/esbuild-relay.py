"""Carry one native esbuild 0.21.5 service through restricted Windows stdio."""

import argparse
import hashlib
import os
import socket
import subprocess
import sys
import threading
from pathlib import Path


ESBUILD_SHA256 = "b868c8d988ffe76006c03c91f856312c312e42e2f3932a6bb56d7f4a1790c8b3"
BUFFER_SIZE = 64 * 1024


def forward_stdin(channel, target):
    try:
        while chunk := channel.recv(BUFFER_SIZE):
            data = memoryview(chunk)
            while data:
                data = data[target.write(data):]
    except OSError:
        pass
    finally:
        target.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("binary", type=Path)
    parser.add_argument("port", type=int, choices=range(1, 65536), metavar="PORT")
    args = parser.parse_args()
    token = os.environ.pop("SPG_WORKSPACE_NPM_TOKEN")
    if len(token) != 64 or not args.binary.is_absolute() or args.binary.name.lower() != "esbuild.exe":
        raise ValueError("invalid esbuild relay invocation")
    with args.binary.open("rb") as handle:
        if hashlib.file_digest(handle, "sha256").hexdigest() != ESBUILD_SHA256:
            raise ValueError("invalid esbuild binary fingerprint")

    with socket.create_connection(("127.0.0.1", args.port), timeout=5) as channel:
        channel.settimeout(None)
        channel.sendall(token.encode("ascii"))
        service = subprocess.Popen([str(args.binary), "--service=0.21.5", "--ping"],
                                   stdin=subprocess.PIPE, stdout=subprocess.PIPE, bufsize=0)
        try:
            threading.Thread(target=forward_stdin, args=(channel, service.stdin), daemon=True).start()
            while chunk := service.stdout.read(BUFFER_SIZE):
                channel.sendall(chunk)
            channel.shutdown(socket.SHUT_WR)
            return service.wait(timeout=3)
        except (OSError, subprocess.TimeoutExpired):
            return 1
        finally:
            if service.poll() is None:
                service.kill()
                service.wait()
            service.stdout.close()


if __name__ == "__main__":
    sys.exit(main())
