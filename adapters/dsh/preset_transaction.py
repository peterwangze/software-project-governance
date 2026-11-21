"""Exclusive directory-preset installation and interrupted-swap recovery."""
from contextlib import contextmanager
import json
import os
from pathlib import Path
import stat
import tempfile


class InstallationBusy(OSError):
    pass


def _redirected(path):
    return path.is_symlink() or bool(getattr(path.lstat(), "st_file_attributes", 0)
                                     & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0))


@contextmanager
def installation_lock(target):
    """The OS drops the lease when the process dies; keep the inode stable."""
    path = target.parent.parent / ("." + target.name + ".install.lock")
    if os.path.lexists(path) and (_redirected(path) or not path.is_file()):
        raise InstallationBusy(f"invalid lock path {path}")
    fd = os.open(path, os.O_RDWR | os.O_CREAT | getattr(os, "O_NOFOLLOW", 0), 0o600)
    with os.fdopen(fd, "r+b") as handle:
        try:
            if os.name == "nt":
                import msvcrt
                msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as exc:
            raise InstallationBusy(f"operation in progress at {target}") from exc
        yield


def journal_path(target):
    return target.parent.parent / ("." + target.name + ".install-state.json")


def record_staging(target, container):
    path = journal_path(target)
    with tempfile.NamedTemporaryFile(dir=path.parent, prefix=path.name + ".", delete=False) as f:
        temp = Path(f.name)
        try:
            f.write(json.dumps({"target": str(target), "stage": container.name}).encode())
            f.flush()
            os.fsync(f.fileno())
        except BaseException:
            f.close()
            temp.unlink(missing_ok=True)
            raise
    try:
        os.replace(temp, path)
    finally:
        temp.unlink(missing_ok=True)


def recover_installation(target, verify, remove):
    """Restore the last complete preset and preserve ambiguous external edits."""
    path = journal_path(target)
    if not os.path.lexists(path):
        return
    if _redirected(path) or not path.is_file():
        raise ValueError(f"unexpected installation journal at {path}")
    state = json.loads(path.read_bytes())
    name = state["stage"]
    if (state.get("target") != str(target) or not isinstance(name, str)
            or Path(name).name != name or not name.startswith(target.name + ".stage-")):
        raise ValueError(f"invalid installation journal at {path}")
    container = target.parent / name
    if os.path.lexists(container) and (_redirected(container) or not container.is_dir()):
        raise ValueError(f"unexpected recovery directory at {container}")
    backup = container / "old"
    if os.path.lexists(backup):
        verify(backup)
        if not os.path.lexists(target):
            backup.rename(target)
        else:
            verify(target)
            remove(backup)
    staging = container / "new"
    if os.path.lexists(staging):
        try:
            verify(staging)
        except (OSError, ValueError, KeyError, TypeError):
            # The interrupted writer may have died halfway through a file.
            # An incomplete/unrecognized tree has no ownership proof. Leave it
            # for inspection while allowing the recovered target to be retried.
            print(f"Preserved incomplete installation staging at {staging}")
        else:
            remove(staging)
    if container.is_dir() and not any(container.iterdir()):
        container.rmdir()
    path.unlink()
