"""Native notice guards use synthetic binaries and license texts only."""

import hashlib
import json
from pathlib import Path

import pytest

from scripts import native_notices as notices
from scripts.release_package import ReleaseError
from tests.test_release_package import put


@pytest.fixture
def source(tmp_path: Path) -> Path:
    root = tmp_path / "source"
    text = "Synthetic copyright and permission notice\n"
    put(root, "release/native-notices/openssl.txt", text)
    catalog = {
        "schema": 1,
        "python": "3.13.17",
        "notices": {
            "openssl.txt": {
                "sha256": hashlib.sha256(text.encode()).hexdigest(),
                "source": "https://example.org/upstream/v1/LICENSE",
            }
        },
        "components": {
            "openssl": {
                "version": "3.5.9",
                "notices": ["openssl.txt"],
                "provenance": "Synthetic pinned build recipe",
            }
        },
    }
    put(root, "release/native-notices/manifest.json", json.dumps(catalog))
    return root


@pytest.fixture
def bundle(tmp_path: Path) -> Path:
    root = tmp_path / "bundle"
    put(root, "_internal/libssl.3.dylib", "Synthetic native payload")
    return root


def test_inventory_copies_pinned_notices_and_records_exact_native_hashes(
    source: Path, bundle: Path
) -> None:
    notices.add_native_notices(source, bundle, "macos-arm64", python_version="3.13.17")
    report = json.loads((bundle / "THIRD_PARTY/NATIVE-LIBRARIES.json").read_text())
    assert report["python"] == "3.13.17"
    assert report["target"] == "macos-arm64"
    assert report["binaries"]["_internal/libssl.3.dylib"]["components"] == ["openssl"]
    assert (
        report["binaries"]["_internal/libssl.3.dylib"]["sha256"]
        == hashlib.sha256((bundle / "_internal/libssl.3.dylib").read_bytes()).hexdigest()
    )
    for prefix in ("THIRD_PARTY", "_internal/THIRD_PARTY"):
        assert (bundle / prefix / "NATIVE/openssl.txt").read_bytes() == (
            source / "release/native-notices/openssl.txt"
        ).read_bytes()
    assert str(source) not in json.dumps(report)
    assert str(bundle) not in json.dumps(report)
    notices.verify_native_notices(bundle, "macos-arm64")


@pytest.mark.parametrize("mutation", ["deleted", "changed", "symlink", "traversal"])
def test_missing_changed_or_unsafe_source_notice_is_refused(
    source: Path, bundle: Path, mutation: str
) -> None:
    path = source / "release/native-notices/openssl.txt"
    if mutation == "deleted":
        path.unlink()
    elif mutation == "changed":
        path.write_text("Unreviewed replacement")
    elif mutation == "symlink":
        path.unlink()
        path.symlink_to(source / "release/native-notices/manifest.json")
    else:
        catalog = source / "release/native-notices/manifest.json"
        data = json.loads(catalog.read_text())
        data["notices"]["../escape.txt"] = data["notices"].pop("openssl.txt")
        catalog.write_text(json.dumps(data))
    with pytest.raises(ReleaseError, match="notice"):
        notices.add_native_notices(source, bundle, "macos-arm64", python_version="3.13.17")
    assert not (bundle / "THIRD_PARTY/NATIVE-LIBRARIES.json").exists()


def test_unreviewed_python_version_is_not_given_assumed_component_versions(
    source: Path, bundle: Path
) -> None:
    with pytest.raises(ReleaseError, match="Python"):
        notices.add_native_notices(source, bundle, "macos-arm64", python_version="3.12.8")


@pytest.mark.parametrize(
    "name", ["_internal/unknown.dylib", "_internal/unknown.so", "_internal/evil.dat"]
)
def test_unknown_native_library_including_disguised_macho_fails_closed(
    source: Path, bundle: Path, name: str
) -> None:
    put(bundle, name, b"\xcf\xfa\xed\xfe".decode("latin1"))
    if name.endswith(".dat"):
        (bundle / name).write_bytes(b"\xcf\xfa\xed\xfe" + b"synthetic")
    with pytest.raises(ReleaseError, match="Unreviewed native"):
        notices.add_native_notices(source, bundle, "macos-arm64", python_version="3.13.17")


@pytest.mark.parametrize(
    "mutation", ["notice", "internal-notice", "binary", "report", "extra", "target"]
)
def test_post_collection_notice_or_binary_mutation_is_rejected(
    source: Path, bundle: Path, mutation: str
) -> None:
    notices.add_native_notices(source, bundle, "macos-arm64", python_version="3.13.17")
    if mutation == "notice":
        (bundle / "THIRD_PARTY/NATIVE/openssl.txt").unlink()
    elif mutation == "internal-notice":
        (bundle / "_internal/THIRD_PARTY/NATIVE/openssl.txt").write_text("changed")
    elif mutation == "binary":
        (bundle / "_internal/libssl.3.dylib").write_text("changed")
    elif mutation == "report":
        (bundle / "THIRD_PARTY/NATIVE-LIBRARIES.json").unlink()
    elif mutation == "extra":
        put(bundle, "_internal/libcrypto.3.dylib", "extra native file")
    with pytest.raises(ReleaseError, match="native|notice|inventory"):
        notices.verify_native_notices(
            bundle, "windows-x64" if mutation == "target" else "macos-arm64"
        )


@pytest.mark.parametrize(
    ("target", "name", "components"),
    [
        ("macos-arm64", "Bowl-Bound", ["pyinstaller"]),
        ("windows-x64", "BowlBound.exe", ["pyinstaller"]),
        ("macos-x86_64", "_internal/libncurses.6.dylib", ["ncurses"]),
        ("windows-x64", "_internal/libcrypto-3.dll", ["openssl"]),
        ("windows-x64", "_internal/libffi-8.dll", ["libffi"]),
        ("windows-x64", "_internal/VCRUNTIME140_1.dll", ["cpython"]),
        ("macos-arm64", "_internal/Python.framework/Versions/3.13/Python", ["cpython"]),
        ("windows-x64", "_internal/yaml/_yaml.cp313-win_amd64.pyd", ["pyyaml", "libyaml"]),
        (
            "macos-arm64",
            "_internal/pydantic_core/_pydantic_core.cpython-313-darwin.so",
            ["pydantic-core"],
        ),
        ("windows-x64", "_internal/_lzma.pyd", ["cpython", "xz"]),
        (
            "macos-x86_64",
            "_internal/python3.13/lib-dynload/_decimal.cpython-313-darwin.so",
            ["cpython", "mpdecimal"],
        ),
    ],
)
def test_reviewed_native_families_have_explicit_component_coverage(
    target: str, name: str, components: list[str]
) -> None:
    assert notices._components(name, target) == components


@pytest.mark.parametrize(
    "mutation",
    ["bad-json", "not-object", "schema", "hash", "source", "reference", "missing-component"],
)
def test_bad_catalog_fails_before_notices_are_written(
    source: Path, bundle: Path, mutation: str
) -> None:
    path = source / "release/native-notices/manifest.json"
    data = json.loads(path.read_text())
    if mutation == "schema":
        data["schema"] = 99
    elif mutation == "hash":
        data["notices"]["openssl.txt"]["sha256"] = "not-a-hash"
    elif mutation == "source":
        data["notices"]["openssl.txt"]["source"] = "/private/local/LICENSE"
    elif mutation == "reference":
        data["components"]["openssl"]["notices"] = ["missing.txt"]
    elif mutation == "missing-component":
        data["components"]["other"] = data["components"].pop("openssl")
    path.write_text(
        "{" if mutation == "bad-json" else json.dumps([] if mutation == "not-object" else data)
    )
    with pytest.raises(ReleaseError, match="notice"):
        notices.add_native_notices(source, bundle, "macos-arm64", python_version="3.13.17")
    assert not (bundle / "THIRD_PARTY").exists()


@pytest.mark.parametrize(
    ("name", "component", "good_marker"),
    [
        ("_internal/libcrypto.3.dylib", "openssl", b"OpenSSL 3.5.9"),
        ("_internal/libncurses.6.dylib", "ncurses", b"ncurses 6.5.20240427"),
        (
            "_internal/pydantic_core/_pydantic_core.cpython-313-darwin.so",
            "pydantic-core",
            b"/rustc/b940084d7eb6a299eb4bfeb8e34901bc051e7ac4/",
        ),
    ],
)
def test_changed_native_version_or_compiler_does_not_inherit_notice_provenance(
    source: Path, bundle: Path, name: str, component: str, good_marker: bytes
) -> None:
    catalog = source / "release/native-notices/manifest.json"
    data = json.loads(catalog.read_text())
    data["components"][component] = {
        "version": "synthetic",
        "notices": ["openssl.txt"],
        "provenance": "Synthetic fixture",
        "binary_marker": good_marker.decode(),
    }
    catalog.write_text(json.dumps(data))
    put(bundle, name, "Synthetic binary with unreviewed or absent version marker")
    with pytest.raises(ReleaseError, match="provenance"):
        notices.add_native_notices(source, bundle, "macos-arm64", python_version="3.13.17")
    (bundle / name).write_bytes(b"synthetic\0" + good_marker + b"\0end")
    notices.add_native_notices(source, bundle, "macos-arm64", python_version="3.13.17")
    notices.verify_native_notices(bundle, "macos-arm64")
