"""Private DSH staging directories, including Windows write-restricted children."""
import ctypes
from ctypes import wintypes
from contextlib import contextmanager
import os
from pathlib import Path
import re
import secrets
import shutil
import tempfile


# Private current-user, SYSTEM and Administrators ACEs, plus one existing DSH
# resource grant. OWNER RIGHTS alone does not identify the restricted user.
# The host's deny prevents a delete through the parent's DELETE_CHILD right.
_PRIVATE = "D:P(D;CI;DT;;;WD)(A;OICI;FA;;;SY)(A;OICI;FA;;;BA)(A;OICI;FA;;;{user_sid})"
_HOST_GRANT = "0x110156"
_READ_ONLY = {"FR", "FX", "FRFX", "FXFR", "GR", "GX", "GRGX", "GXGR", "RC"}


def _private_descriptor(parent_descriptor, restrictions, user_sid):
    """Recognize the native grant on this parent; never copy ambient allow ACEs."""
    owner, delimiter, dacl = parent_descriptor.partition("D:")
    if owner != "O:" + user_sid or not delimiter:
        raise PermissionError("DSH temporary parent is not owned by the calling user")
    parent_dacl = delimiter + dacl
    if not re.fullmatch(r"D:[A-Z]*(?:\([^()]+\))+", parent_dacl):
        raise PermissionError("unsupported DSH parent DACL")
    grants = set()
    delete_guard = False
    entries = re.findall(r"\(([^()]*)\)", parent_dacl)
    for entry in entries:
        fields = entry.split(";")
        if len(fields) != 6:
            raise PermissionError("unsupported DSH parent ACE")
        kind, flags, rights, object_id, inherited_id, sid = fields
        if object_id or inherited_id or kind not in {"A", "D"}:
            raise PermissionError("unsupported ACL on the DSH temporary parent")
        flags = flags.removesuffix("ID")
        if kind == "D":
            if (flags, rights, sid) != ("CI", "DT", "WD"):
                raise PermissionError("additional deny ACL on the DSH temporary parent")
            delete_guard = True
        elif (flags == "OICI" and rights == _HOST_GRANT and sid in restrictions
              and re.fullmatch(r"S-1-4-\d+-\d+(?:-1)?", sid)):
            grants.add(sid)
        elif sid not in {user_sid, "OW", "SY", "BA"} and rights not in _READ_ONLY:
            raise PermissionError("untrusted writable principal on the DSH temporary parent")
    if not delete_guard or len(grants) != 1:
        raise PermissionError("temporary parent lacks an unambiguous DSH sandbox directory grant")
    return _PRIVATE.format(user_sid=user_sid) + f"(A;OICI;{_HOST_GRANT};;;{grants.pop()})"


@contextmanager
def _allocated(kernel, pointer):
    try:
        yield pointer
    finally:
        kernel.LocalFree(ctypes.cast(pointer, ctypes.c_void_p))


def _required(success):
    if not success:
        raise ctypes.WinError(ctypes.get_last_error())


def _restrictions(api, kernel):
    class Group(ctypes.Structure):
        _fields_ = [("sid", ctypes.c_void_p), ("attributes", wintypes.DWORD)]

    class Groups(ctypes.Structure):
        _fields_ = [("count", wintypes.DWORD), ("first", Group)]

    def token_info(token, kind):
        size = wintypes.DWORD()
        api.GetTokenInformation(token, kind, None, 0, ctypes.byref(size))
        if ctypes.get_last_error() != 122:  # ERROR_INSUFFICIENT_BUFFER
            raise ctypes.WinError(ctypes.get_last_error())
        buf = ctypes.create_string_buffer(size.value)
        _required(api.GetTokenInformation(token, kind, buf, len(buf), ctypes.byref(size)))
        return buf

    def sid_text(sid):
        text = wintypes.LPWSTR()
        _required(api.ConvertSidToStringSidW(ctypes.c_void_p(sid), ctypes.byref(text)))
        with _allocated(kernel, text):
            return text.value

    token = wintypes.HANDLE()
    _required(api.OpenProcessToken(wintypes.HANDLE(-1), 8, ctypes.byref(token)))
    try:
        buf = token_info(token, 11)  # TokenRestrictedSids
        count = wintypes.DWORD.from_buffer(buf).value
        if not count:
            return set(), None
        groups = (Group * count).from_buffer(buf, Groups.first.offset)
        user = token_info(token, 1)  # TokenUser
        return {sid_text(g.sid) for g in groups}, sid_text(Group.from_buffer(user).sid)
    finally:
        kernel.CloseHandle(token)


def _parent_security(api, kernel, parent):
    binary = ctypes.c_void_p()
    rc = api.GetNamedSecurityInfoW(str(parent), 1, 5, None, None, None, None, ctypes.byref(binary))
    if rc:
        raise ctypes.WinError(rc)
    with _allocated(kernel, binary):
        text = wintypes.LPWSTR()
        _required(api.ConvertSecurityDescriptorToStringSecurityDescriptorW(
            binary, 1, 5, ctypes.byref(text), None))
        with _allocated(kernel, text):
            return text.value


def _windows_private_dir(prefix, parent):
    api = ctypes.WinDLL("advapi32", use_last_error=True)
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    restrictions, user_sid = _restrictions(api, kernel)
    if not restrictions:
        return Path(tempfile.mkdtemp(prefix=prefix, dir=parent))
    parent = Path(tempfile.gettempdir() if parent is None else parent)
    sddl = _private_descriptor(_parent_security(api, kernel, parent), restrictions, user_sid)

    class SecurityAttributes(ctypes.Structure):
        _fields_ = [("length", wintypes.DWORD), ("descriptor", ctypes.c_void_p), ("inherit", wintypes.BOOL)]

    binary = ctypes.c_void_p()
    _required(api.ConvertStringSecurityDescriptorToSecurityDescriptorW(sddl, 1, ctypes.byref(binary), None))
    with _allocated(kernel, binary):
        attributes = SecurityAttributes(ctypes.sizeof(SecurityAttributes), binary, False)
        for _ in range(16):
            path = parent / (prefix + secrets.token_hex(16))
            if kernel.CreateDirectoryW(str(path), ctypes.byref(attributes)):
                return path
            error = ctypes.get_last_error()
            if error != 183:  # ERROR_ALREADY_EXISTS
                raise ctypes.WinError(error)
    raise FileExistsError("unable to reserve a unique DSH temporary directory")


def make_private_dir(prefix, parent=None):
    if not prefix or Path(prefix).name != prefix:
        raise ValueError("expected a temporary directory name prefix")
    if os.name == "nt":
        return _windows_private_dir(prefix, parent)
    return Path(tempfile.mkdtemp(prefix=prefix, dir=parent))


@contextmanager
def private_dir(prefix, parent):
    path = make_private_dir(prefix, parent)
    try:
        yield path
    finally:
        shutil.rmtree(path)
