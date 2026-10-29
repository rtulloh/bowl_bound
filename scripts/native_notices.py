"""Offline, hash-pinned notices and per-binary inventory for native releases.

This is an engineering coverage guard, not a legal opinion or an inference of
static dependency provenance from a library filename. See the reviewed catalog.
"""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

from .release_package import ReleaseError, _plain, _write_json

TARGETS = {"macos-arm64", "macos-x86_64", "windows-x64"}
ROOTS = ("THIRD_PARTY", "_internal/THIRD_PARTY")
STDLIB_EXTENSIONS = frozenset(
    "_asyncio _bisect _blake2 _bz2 _codecs_cn _codecs_hk _codecs_iso2022 _codecs_jp "
    "_codecs_kr _codecs_tw _contextvars _csv _ctypes _curses _datetime _decimal "
    "_hashlib _heapq _interpqueues _interpreters _json _lzma _md5 _multibytecodec "
    "_multiprocessing _opcode _overlapped _pickle _posixshmem _posixsubprocess "
    "_queue _random _scproxy _sha1 _sha2 _sha3 _socket _ssl _statistics _struct "
    "_uuid _wmi _zoneinfo array binascii fcntl grp math mmap pyexpat readline "
    "resource select syslog termios unicodedata zlib".split()
)
MAGICS = {
    b"\xcf\xfa\xed\xfe",
    b"\xce\xfa\xed\xfe",
    b"\xfe\xed\xfa\xcf",
    b"\xfe\xed\xfa\xce",
    b"\xca\xfe\xba\xbe",
    b"\xbe\xba\xfe\xca",
    b"\x7fELF",
}


def _digest(path: Path) -> str:
    return hashlib.sha256(_plain(path).read_bytes()).hexdigest()


def _json(path: Path) -> dict:
    try:
        value = json.loads(_plain(path).read_text(encoding="utf-8"))
    except (OSError, ValueError) as error:
        raise ReleaseError("Missing or invalid native notice inventory") from error
    if not isinstance(value, dict):
        raise ReleaseError("Invalid native notice inventory")
    return value


def _catalog(data: dict) -> None:
    """Validate paths and references before any notice is copied."""
    try:
        if data["schema"] != 1 or not re.fullmatch(r"\d+\.\d+\.\d+", data["python"]):
            raise ValueError
        if not data["notices"] or not data["components"]:
            raise ValueError
        for name, entry in data["notices"].items():
            if not re.fullmatch(r"[a-zA-Z0-9][a-zA-Z0-9_.-]*", name):
                raise ValueError
            if not re.fullmatch(r"[a-f0-9]{64}", entry["sha256"]):
                raise ValueError
            if not entry["source"].startswith("https://"):
                raise ValueError
        for name, component in data["components"].items():
            if not re.fullmatch(r"[a-z0-9-]+", name):
                raise ValueError
            if not component["version"] or not component["provenance"] or not component["notices"]:
                raise ValueError
            if not set(component["notices"]) <= data["notices"].keys():
                raise ValueError
    except (KeyError, TypeError, AttributeError, ValueError) as error:
        raise ReleaseError("Invalid native notice catalog") from error


def _native_files(bundle: Path) -> dict[str, str]:
    result = {}
    for path in sorted(bundle.rglob("*")):
        _plain(path)
        if path.is_dir():
            continue
        with path.open("rb") as stream:
            header = stream.read(4)
        if path.suffix.lower() in {".dll", ".dylib", ".so", ".pyd"} or (
            header in MAGICS or header.startswith(b"MZ")
        ):
            result[path.relative_to(bundle).as_posix()] = _digest(path)
    return result


def _components(name: str, target: str) -> list[str]:
    """Classify only reviewed runtime families; unknown native code fails closed."""
    filename = Path(name).name
    if name == ("BowlBound.exe" if target == "windows-x64" else "Bowl-Bound"):
        return ["pyinstaller"]
    if not name.startswith("_internal/"):
        raise ReleaseError(f"Unreviewed native library: {name}")
    windows = target == "windows-x64"
    if name == "_internal/" + filename and filename in (
        {"libssl-3.dll", "libcrypto-3.dll"} if windows else {"libssl.3.dylib", "libcrypto.3.dylib"}
    ):
        return ["openssl"]
    if not windows and name == "_internal/libncurses.6.dylib":
        return ["ncurses"]
    if windows and name == "_internal/libffi-8.dll":
        return ["libffi"]
    if windows and re.fullmatch(
        r"_internal/(?:python313|VCRUNTIME140(?:_1)?|ucrtbase|api-ms-win-[a-z0-9-]+)\.dll", name
    ):
        return ["cpython"]
    if not windows and re.fullmatch(
        r"_internal/(?:Python|Python\.framework/(?:Python|Versions/(?:3\.13|Current)/Python))", name
    ):
        return ["cpython"]
    tag = r"cp313-win_amd64\.pyd" if windows else r"cpython-313-darwin\.so"
    if re.fullmatch(r"_internal/yaml/_yaml\." + tag, name):
        return ["pyyaml", "libyaml"]
    if re.fullmatch(r"_internal/pydantic_core/_pydantic_core\." + tag, name):
        return ["pydantic-core"]
    module = filename.split(".")[0]
    stdpath = "_internal/" + filename if windows else "_internal/python3.13/lib-dynload/" + filename
    if (
        name == stdpath
        and module in STDLIB_EXTENSIONS
        and (filename.endswith(".pyd") if windows else filename.endswith(".cpython-313-darwin.so"))
    ):
        extras = {
            "_bz2": ["bzip2"],
            "_lzma": ["xz"],
            "_decimal": ["mpdecimal"],
            "pyexpat": ["expat"],
            "zlib": ["zlib"],
            "binascii": ["zlib"],
        }
        return ["cpython", *extras.get(module, [])]
    raise ReleaseError(f"Unreviewed native library: {name}")


def _verify_provenance(bundle: Path, name: str, data: dict) -> None:
    """Require observed upstream version/compiler markers, not just plausible filenames."""
    filename = Path(name).name
    component = next(
        (
            component
            for prefix, component in (
                ("libcrypto", "openssl"),
                ("libncurses", "ncurses"),
                ("_pydantic_core.", "pydantic-core"),
            )
            if filename.startswith(prefix)
        ),
        None,
    )
    if component is None:
        return
    marker = data["components"][component].get("binary_marker")
    if not isinstance(marker, str) or not marker:
        raise ReleaseError(f"Missing native provenance marker for {name}")
    pattern = re.escape(marker.encode("utf-8"))
    if not marker.endswith("/"):
        pattern += rb"(?![A-Za-z0-9.])"
    if re.search(pattern, _plain(bundle / name).read_bytes()) is None:
        raise ReleaseError(f"Unreviewed native provenance for {name}")


def add_native_notices(source: Path, bundle: Path, target: str, *, python_version: str) -> None:
    """Copy only reviewed notice bytes and record native hashes, without network access."""
    catalog_root = source / "release/native-notices"
    data = _json(catalog_root / "manifest.json")
    _catalog(data)
    if target not in TARGETS or python_version != data["python"]:
        raise ReleaseError("Native notice catalog requires the reviewed Python version and target")
    texts = {}
    for name, entry in data["notices"].items():
        try:
            path = catalog_root / name
            if _digest(path) != entry["sha256"]:
                raise ValueError
            texts[name] = path.read_bytes()
        except (OSError, ValueError, ReleaseError) as error:
            raise ReleaseError(f"Missing, unsafe or changed native notice: {name}") from error
    binaries = {}
    for name, digest in _native_files(bundle).items():
        components = _components(name, target)
        if not set(components) <= data["components"].keys():
            raise ReleaseError(f"Missing native notice component for {name}")
        _verify_provenance(bundle, name, data)
        binaries[name] = {"sha256": digest, "components": components}
    report = {
        "schema": 1,
        "python": python_version,
        "target": target,
        "catalog": data,
        "binaries": binaries,
    }
    for root in ROOTS:
        destination = bundle / root
        destination.mkdir(parents=True, exist_ok=True)
        native = destination / "NATIVE"
        native.mkdir()
        for name, text in texts.items():
            (native / name).write_bytes(text)
        _write_json(destination, "NATIVE-LIBRARIES.json", report)


def verify_native_notices(bundle: Path, target: str) -> None:
    """Refuse missing/changed notice bytes or unaccounted native binaries before ZIP creation."""
    actual = _native_files(bundle)
    if not actual and not (bundle / ROOTS[0] / "NATIVE-LIBRARIES.json").exists():
        return  # Synthetic archive fixtures contain no native executable or libraries.
    report = _json(bundle / ROOTS[0] / "NATIVE-LIBRARIES.json")
    try:
        data = report["catalog"]
        _catalog(data)
        if (
            report["schema"] != 1
            or report["target"] != target
            or report["python"] != data["python"]
        ):
            raise ValueError
        expected = {
            name: {"sha256": digest, "components": _components(name, target)}
            for name, digest in actual.items()
        }
        if report["binaries"] != expected:
            raise ValueError
        if any(
            not set(item["components"]) <= data["components"].keys() for item in expected.values()
        ):
            raise ValueError
        for name in expected:
            _verify_provenance(bundle, name, data)
        for root in ROOTS:
            if _json(bundle / root / "NATIVE-LIBRARIES.json") != report:
                raise ValueError
            for name, entry in data["notices"].items():
                if _digest(bundle / root / "NATIVE" / name) != entry["sha256"]:
                    raise ValueError
    except (OSError, KeyError, TypeError, ValueError) as error:
        raise ReleaseError("Native notice or binary inventory changed or is incomplete") from error
