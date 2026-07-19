"""Protect locally stored credentials with the Windows user profile.

New values use Windows DPAPI, so they can only be decrypted by the current
Windows user on this machine.  The old ``enc:`` XOR format remains readable
solely to migrate existing installs when they next save their configuration.
"""

from __future__ import annotations

import base64
import ctypes
import hashlib
import os
import platform
import uuid
from ctypes import wintypes


_DPAPI_PREFIX = "dpapi:"
_LEGACY_PREFIX = "enc:"
_CRYPTPROTECT_UI_FORBIDDEN = 0x1


class _DataBlob(ctypes.Structure):
    _fields_ = [
        ("cbData", wintypes.DWORD),
        ("pbData", ctypes.POINTER(ctypes.c_byte)),
    ]


def _get_machine_key() -> bytes:
    """Compatibility-only key for reading pre-DPAPI ``enc:`` values."""
    try:
        machine_name = platform.node()
        mac_address = str(uuid.getnode())
    except Exception:
        machine_name = "unknown"
        mac_address = "000000000000"
    raw = f"{machine_name}|{mac_address}|t2studio-key-salt-v1-2026"
    return hashlib.sha256(raw.encode("utf-8")).digest()


def _xor_cipher(data: bytes, key: bytes) -> bytes:
    return bytes(b ^ key[i % len(key)] for i, b in enumerate(data))


def _blob(data: bytes) -> tuple[_DataBlob, ctypes.Array[ctypes.c_char]]:
    buffer = ctypes.create_string_buffer(data)
    return (
        _DataBlob(
            len(data),
            ctypes.cast(buffer, ctypes.POINTER(ctypes.c_byte)),
        ),
        buffer,
    )


def _crypt32():
    if os.name != "nt":
        raise RuntimeError("Lưu credential mã hoá chỉ được hỗ trợ trên Windows.")
    crypt32 = ctypes.WinDLL("Crypt32", use_last_error=True)
    crypt32.CryptProtectData.argtypes = [
        ctypes.POINTER(_DataBlob),
        ctypes.c_wchar_p,
        ctypes.POINTER(_DataBlob),
        ctypes.c_void_p,
        ctypes.c_void_p,
        wintypes.DWORD,
        ctypes.POINTER(_DataBlob),
    ]
    crypt32.CryptProtectData.restype = wintypes.BOOL
    crypt32.CryptUnprotectData.argtypes = [
        ctypes.POINTER(_DataBlob),
        ctypes.POINTER(ctypes.c_wchar_p),
        ctypes.POINTER(_DataBlob),
        ctypes.c_void_p,
        ctypes.c_void_p,
        wintypes.DWORD,
        ctypes.POINTER(_DataBlob),
    ]
    crypt32.CryptUnprotectData.restype = wintypes.BOOL
    return crypt32


def _free_blob(blob: _DataBlob) -> None:
    if not blob.pbData:
        return
    kernel32 = ctypes.WinDLL("Kernel32", use_last_error=True)
    kernel32.LocalFree.argtypes = [ctypes.c_void_p]
    kernel32.LocalFree.restype = ctypes.c_void_p
    kernel32.LocalFree(ctypes.cast(blob.pbData, ctypes.c_void_p))


def _protect(data: bytes) -> bytes:
    source, _source_buffer = _blob(data)
    protected = _DataBlob()
    if not _crypt32().CryptProtectData(
        ctypes.byref(source),
        "TubeCraft credential",
        None,
        None,
        None,
        _CRYPTPROTECT_UI_FORBIDDEN,
        ctypes.byref(protected),
    ):
        raise ctypes.WinError(ctypes.get_last_error())
    try:
        return ctypes.string_at(protected.pbData, protected.cbData)
    finally:
        _free_blob(protected)


def _unprotect(data: bytes) -> bytes:
    source, _source_buffer = _blob(data)
    plaintext = _DataBlob()
    if not _crypt32().CryptUnprotectData(
        ctypes.byref(source),
        None,
        None,
        None,
        None,
        _CRYPTPROTECT_UI_FORBIDDEN,
        ctypes.byref(plaintext),
    ):
        raise ctypes.WinError(ctypes.get_last_error())
    try:
        return ctypes.string_at(plaintext.pbData, plaintext.cbData)
    finally:
        _free_blob(plaintext)


def encrypt_value(plaintext: str) -> str:
    """Encrypt a secret for the current Windows user using DPAPI."""
    if not isinstance(plaintext, str):
        raise TypeError("Credential phải là chuỗi.")
    if plaintext.startswith(_DPAPI_PREFIX):
        return plaintext
    return _DPAPI_PREFIX + base64.b64encode(_protect(plaintext.encode("utf-8"))).decode(
        "ascii"
    )


def is_dpapi_value(value: object) -> bool:
    """Whether a persisted credential already has current-user protection."""

    return isinstance(value, str) and value.startswith(_DPAPI_PREFIX)


def decrypt_value(ciphertext: str) -> str:
    """Decrypt DPAPI values; callers may migrate legacy plaintext/XOR values."""
    if not isinstance(ciphertext, str):
        return ""
    if ciphertext.startswith(_DPAPI_PREFIX):
        try:
            payload = base64.b64decode(ciphertext[len(_DPAPI_PREFIX) :], validate=True)
            return _unprotect(payload).decode("utf-8")
        except Exception:
            # Never pass an unreadable encrypted blob to a remote API as if it
            # were a credential.
            return ""
    if ciphertext.startswith(_LEGACY_PREFIX):
        try:
            payload = base64.b64decode(ciphertext[len(_LEGACY_PREFIX) :], validate=True)
            return _xor_cipher(payload, _get_machine_key()).decode("utf-8")
        except Exception:
            return ""
    return ciphertext
