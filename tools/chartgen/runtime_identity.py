"""Bind local research attestations to loaded Python sources and callable code.

This is a reproducibility guard, not a sandbox or proof of historical accuracy.
It rejects mixed checkouts and changed handwritten Python code before a research
contract is emitted. Generated dataclass/enum methods are not source functions.
"""

from __future__ import annotations

import ast
import contextlib
import dataclasses
import hashlib
import importlib.util
import inspect
import reprlib
import sys
from collections.abc import Iterator, Mapping
from dataclasses import is_dataclass
from enum import Enum
from functools import _lru_cache_wrapper
from pathlib import Path
from types import CodeType, FunctionType, ModuleType
from typing import Any

RESEARCH_ROOT = Path(__file__).resolve().parents[2]
# Chart instances sent to a worker are run inputs, separately hashed in contracts.
_RUNTIME_STATE = {
    "tools.chartgen.cohort_simulation": {
        "_WORKER_TEAMS",
        "_WORKER_RUNTIME_SHA256",
        "_WORKER_RESEARCH_INPUTS",
    }
}


def _code_bytes(code: CodeType) -> bytes:
    """Ignore checkout locations, retaining all executable code and constants."""
    fields = (
        code.co_name,
        code.co_argcount,
        code.co_posonlyargcount,
        code.co_kwonlyargcount,
        code.co_nlocals,
        code.co_stacksize,
        code.co_flags,
        code.co_code.hex(),
        tuple(_constant(value) for value in code.co_consts),
        code.co_names,
        code.co_varnames,
        code.co_freevars,
        code.co_cellvars,
        code.co_firstlineno,
        code.co_linetable.hex(),
        getattr(code, "co_exceptiontable", b"").hex(),
    )
    return repr(fields).encode()


def _constant(value: object) -> object:
    if isinstance(value, CodeType):
        return ("code", _code_bytes(value).hex())
    if isinstance(value, tuple):
        return ("tuple", tuple(_constant(item) for item in value))
    if isinstance(value, frozenset):
        return ("frozenset", tuple(sorted(repr(_constant(item)) for item in value)))
    if isinstance(value, dict):
        return (
            "dict",
            tuple(
                sorted(((_constant(key), _constant(item)) for key, item in value.items()), key=repr)
            ),
        )
    if isinstance(value, FunctionType):
        return (
            "function",
            value.__module__,
            value.__qualname__,
            hashlib.sha256(_code_bytes(value.__code__)).hexdigest(),
        )
    if isinstance(value, type):
        return ("type", value.__module__, value.__qualname__)
    if isinstance(value, set):
        return ("set", tuple(sorted(repr(_constant(item)) for item in value)))
    return (type(value).__name__, repr(value))


def _compiled_functions(code: CodeType, prefix: str = "") -> Iterator[tuple[str, CodeType]]:
    for value in code.co_consts:
        if isinstance(value, CodeType):
            qualified = prefix + value.co_name
            yield qualified, value
            nested = qualified + (".<locals>." if value.co_flags & inspect.CO_NEWLOCALS else ".")
            yield from _compiled_functions(value, nested)


def _closure(function: FunctionType) -> dict[str, object]:
    try:
        return {
            name: cell.cell_contents
            for name, cell in zip(
                function.__code__.co_freevars, function.__closure__ or (), strict=True
            )
        }
    except ValueError as error:
        raise ValueError("research runtime callable has an invalid closure") from error


def _functions(
    module: ModuleType, declarations: set[str]
) -> Iterator[tuple[str, str, FunctionType, bool, bool]]:
    """Enumerate handwritten module functions and locally declared methods."""
    for name, value in sorted(vars(module).items()):
        if inspect.isclass(value) and value.__module__ == module.__name__:
            values = ((f"{name}.{key}", item) for key, item in sorted(vars(value).items()))
            generated_owner = is_dataclass(value)
        else:
            values = ((name, value),)
            generated_owner = False
        for label, item in values:
            if isinstance(item, (staticmethod, classmethod)):
                item = item.__func__
            if isinstance(item, property):
                candidates = (item.fget, item.fset, item.fdel)
            else:
                candidates = (item,)
            for index, function in enumerate(candidates):
                if function is None:
                    continue
                if not callable(function) and label not in declarations:
                    continue
                if (
                    label not in declarations
                    and getattr(function, "__module__", None) != module.__name__
                ):
                    continue
                seen: set[int] = set()
                depth = 0
                declaration = label
                if label not in declarations and not generated_owner:
                    declaration = getattr(function, "__qualname__", label)
                while function is not None:
                    if id(function) in seen:
                        raise ValueError(
                            f"research runtime callable wrapper cycle: {module.__name__}.{label}"
                        )
                    seen.add(id(function))
                    if type(function) is _lru_cache_wrapper:
                        function = function.__wrapped__
                        depth += 1
                        continue  # C wrapper parameters are source-checked below.
                    if not isinstance(function, FunctionType):
                        raise ValueError(
                            f"research runtime callable is opaque: {module.__name__}.{label}"
                        )
                    wrapped = getattr(function, "__wrapped__", None)
                    yield (
                        f"{label}/{index}/{depth}",
                        declaration,
                        function,
                        generated_owner and label not in declarations,
                        wrapped is not None,
                    )
                    function = wrapped
                    depth += 1


def _declarations(nodes: list[ast.stmt], prefix: str = "") -> set[str]:
    result: set[str] = set()
    for node in nodes:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            result.add(prefix + node.name)
        elif isinstance(node, ast.ClassDef):
            result.update(_declarations(node.body, prefix + node.name + "."))
        elif isinstance(node, ast.If):
            result.update(_declarations(node.body, prefix))
            result.update(_declarations(node.orelse, prefix))
    return result


def _decorators(nodes: list[ast.stmt], prefix: str = "") -> dict[str, set[str]]:
    result: dict[str, set[str]] = {}
    for node in nodes:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            names: set[str] = set()
            for decorator in node.decorator_list:
                value = decorator.func if isinstance(decorator, ast.Call) else decorator
                if isinstance(value, ast.Name):
                    names.add(value.id)
            result[prefix + node.name] = names
        elif isinstance(node, ast.ClassDef):
            result.update(_decorators(node.body, prefix + node.name + "."))
        elif isinstance(node, ast.If):
            result.update(_decorators(node.body, prefix))
            result.update(_decorators(node.orelse, prefix))
    return result


def _imports(nodes: list[ast.stmt]) -> Iterator[ast.ImportFrom]:
    for node in nodes:
        if isinstance(node, ast.ImportFrom):
            yield node
        elif isinstance(node, ast.If):
            yield from _imports(node.body)
            yield from _imports(node.orelse)


def _check_import_bindings(
    module: ModuleType, source: bytes, modules: Mapping[str, ModuleType]
) -> None:
    for node in _imports(ast.parse(source).body):
        imported = "." * node.level + (node.module or "")
        if node.level:
            imported = importlib.util.resolve_name(imported, module.__package__)
        target = modules.get(imported)
        if target is None:
            continue
        for alias in node.names:
            local = alias.asname or alias.name
            if local not in vars(module):  # e.g. a TYPE_CHECKING-only import
                continue
            if getattr(module, local) is not getattr(target, alias.name, None):
                raise ValueError(
                    f"research runtime callable binding mismatch: {module.__name__}.{local}"
                )


def _literal(node: ast.AST, values: Mapping[str, object]) -> object:
    if isinstance(node, ast.Name):
        return values[node.id]
    if isinstance(node, (ast.Tuple, ast.List, ast.Set)):
        items = [_literal(item, values) for item in node.elts]
        return (
            tuple(items)
            if isinstance(node, ast.Tuple)
            else (set(items) if isinstance(node, ast.Set) else items)
        )
    if isinstance(node, ast.Dict):
        return {
            _literal(key, values): _literal(value, values)
            for key, value in zip(node.keys, node.values, strict=True)
        }
    return ast.literal_eval(node)


def _check_declared_state(
    module: ModuleType,
    nodes: list[ast.stmt],
    owner: object | None = None,
    inherited: Mapping[str, object] | None = None,
) -> None:
    """Check source-literal policy constants and defaults without executing code."""
    owner = module if owner is None else owner
    values = dict(inherited or {})
    for node in nodes:
        if isinstance(node, ast.ClassDef):
            value = vars(owner).get(node.name)
            if not inspect.isclass(value) or value.__module__ != module.__name__:
                raise ValueError(f"research runtime class replaced: {module.__name__}.{node.name}")
            _check_declared_state(module, node.body, value, values)
        elif isinstance(node, (ast.Assign, ast.AnnAssign)) and node.value is not None:
            try:
                expected = _literal(node.value, values)
            except (ValueError, TypeError, KeyError):
                continue
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            for target in targets:
                if not isinstance(target, ast.Name):
                    continue
                values[target.id] = expected
                if (
                    target.id.lstrip("_").isupper()
                    and not (inspect.isclass(owner) and issubclass(owner, Enum))
                    and target.id not in _RUNTIME_STATE.get(module.__name__, set())
                    and vars(owner).get(target.id) != expected
                ):
                    raise ValueError(
                        "research runtime constant differs from source: "
                        f"{module.__name__}.{target.id}"
                    )
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            function = vars(owner).get(node.name)
            if isinstance(function, (staticmethod, classmethod)):
                function = function.__func__
            if isinstance(function, property):
                continue  # Handwritten property code is verified separately above.
            cache = next(
                (
                    decorator
                    for decorator in node.decorator_list
                    if isinstance(decorator, ast.Call)
                    and isinstance(decorator.func, ast.Name)
                    and decorator.func.id == "lru_cache"
                ),
                None,
            )
            if cache is not None:
                parameters = {"maxsize": 128, "typed": False}
                parameters.update(
                    {keyword.arg: ast.literal_eval(keyword.value) for keyword in cache.keywords}
                )
                if (
                    type(function) is not _lru_cache_wrapper
                    or function.cache_parameters() != parameters
                ):
                    raise ValueError(
                        f"research runtime callable cache differs: {module.__name__}.{node.name}"
                    )
            elif type(function) is _lru_cache_wrapper:
                raise ValueError(
                    f"research runtime cache wrapper is undeclared: {module.__name__}.{node.name}"
                )
            function = inspect.unwrap(function)
            if not isinstance(function, FunctionType) or function.__module__ != module.__name__:
                raise ValueError(
                    f"research runtime callable replaced: {module.__name__}.{node.name}"
                )
            try:
                defaults = tuple(_literal(item, values) for item in node.args.defaults) or None
                keyword_defaults = {
                    arg.arg: _literal(item, values)
                    for arg, item in zip(node.args.kwonlyargs, node.args.kw_defaults, strict=True)
                    if item is not None
                } or None
            except (ValueError, TypeError, KeyError):
                continue  # Nonliteral factories are covered by source/code identity.
            if function.__defaults__ != defaults or function.__kwdefaults__ != keyword_defaults:
                raise ValueError(
                    f"research runtime defaults differ from source: {module.__name__}.{node.name}"
                )


def attest_runtime(bindings: Mapping[str, object]) -> dict[str, Any]:
    """Reject foreign module origins/bindings and source-inconsistent loaded code.

    Relative paths make the receipt portable between exact checkouts. The module
    inventory records what is loaded when called, so newly imported research
    components require a new contract rather than reusing an older receipt.
    """
    required: set[str] = {"tools.chartgen.research_runner"}
    for package in ("bowl_bound", "tools.chartgen"):
        directory = RESEARCH_ROOT.joinpath(*package.split("."))
        required.add(package)
        for path in sorted(directory.rglob("*.py")):
            if path.name == "__main__.py":
                continue
            relative = path.relative_to(directory).with_suffix("")
            parts = relative.parts[:-1] if relative.name == "__init__" else relative.parts
            required.add(".".join((package, *parts)))
    for name in sorted(required):
        importlib.import_module(name)
    modules = {
        name: module
        for name, module in tuple(sys.modules.items())
        if module is not None
        and (
            name in required or name.startswith("bowl_bound.") or name.startswith("tools.chartgen.")
        )
        and not name.endswith(".__main__")
    }
    records: dict[str, Any] = {}
    wrapper_sources: dict[str, str] = {}
    standard_codes_cache: dict[str, dict[str, CodeType]] = {}
    actual_code = hashlib.sha256()
    for name, module in sorted(modules.items()):
        relative = Path(*name.split("."))
        expected = RESEARCH_ROOT / relative.with_suffix(".py")
        if not expected.is_file():
            expected = RESEARCH_ROOT / relative / "__init__.py"
        origins = (getattr(module, "__file__", None), getattr(module.__spec__, "origin", None))
        if not expected.is_file() or any(
            origin is None or Path(origin).resolve() != expected.resolve() for origin in origins
        ):
            raise ValueError(f"research runtime module origin mismatch: {name}")
        source = expected.read_bytes()
        tree = ast.parse(source)
        decorators = _decorators(tree.body)
        _check_import_bindings(module, source, modules)
        _check_declared_state(module, tree.body)
        compiled = compile(source, str(expected), "exec", dont_inherit=True)
        expected_code: dict[str, set[bytes]] = {}
        for qualified, code in _compiled_functions(compiled):
            expected_code.setdefault(qualified, set()).add(_code_bytes(code))
        module_code = hashlib.sha256()
        generated_count = 0
        for label, declaration, function, generated, wrapper in _functions(
            module, _declarations(tree.body)
        ):
            code = function.__code__
            encoded = _code_bytes(code)
            if generated and code.co_filename == "<string>":
                # Observed generated code is pinned on reuse, not called source-verified.
                generated_count += 1
            elif wrapper and Path(code.co_filename).resolve() != expected.resolve():
                known = next(
                    (
                        standard
                        for standard in (contextlib, dataclasses, reprlib)
                        if Path(code.co_filename).resolve() == Path(standard.__file__).resolve()
                    ),
                    None,
                )
                if known is None:
                    raise ValueError(
                        f"research runtime callable wrapper origin mismatch: {name}.{label}"
                    )
                if function.__globals__ is not vars(known):
                    raise ValueError(f"research runtime wrapper globals mismatch: {name}.{label}")
                if not (
                    (known is contextlib and "contextmanager" in decorators.get(declaration, set()))
                    or (known in (dataclasses, reprlib) and generated)
                ):
                    raise ValueError(f"research runtime wrapper is undeclared: {name}.{label}")
                if known.__name__ not in standard_codes_cache:
                    standard_source = Path(known.__file__).read_bytes()
                    standard_codes_cache[known.__name__] = dict(
                        _compiled_functions(
                            compile(
                                standard_source,
                                known.__file__,
                                "exec",
                                dont_inherit=True,
                            )
                        )
                    )
                    wrapper_sources[known.__name__] = hashlib.sha256(standard_source).hexdigest()
                standard_codes = standard_codes_cache[known.__name__]
                qualified = getattr(code, "co_qualname", "")
                if not qualified:  # Python 3.10 has no code.co_qualname.
                    qualified = next(
                        (
                            key
                            for key, item in standard_codes.items()
                            if item.co_name == code.co_name
                            and item.co_firstlineno == code.co_firstlineno
                        ),
                        "",
                    )
                expected_wrapper = standard_codes.get(qualified)
                if expected_wrapper is None or encoded != _code_bytes(expected_wrapper):
                    raise ValueError(
                        f"research runtime wrapper code differs from source: {name}.{label}"
                    )
                cells = _closure(function)
                target = function.__wrapped__
                valid_closure = (
                    (
                        known is contextlib
                        and qualified == "contextmanager.<locals>.helper"
                        and set(cells) == {"func"}
                        and cells["func"] is target
                    )
                    or (
                        known is dataclasses
                        and qualified == "_recursive_repr.<locals>.wrapper"
                        and set(cells) == {"repr_running", "user_function"}
                        and cells["user_function"] is target
                        and type(cells["repr_running"]) is set
                    )
                    or (
                        known is reprlib
                        and qualified
                        == "recursive_repr.<locals>.decorating_function.<locals>.wrapper"
                        and set(cells) == {"fillvalue", "repr_running", "user_function"}
                        and cells["user_function"] is target
                        and cells["fillvalue"] == "..."
                        and type(cells["repr_running"]) is set
                    )
                )
                if not valid_closure:
                    raise ValueError(
                        f"research runtime callable wrapper closure mismatch: {name}.{label}"
                    )
            else:
                if function.__globals__ is not vars(module):
                    raise ValueError(f"research runtime callable globals mismatch: {name}.{label}")
                if Path(code.co_filename).resolve() != expected.resolve():
                    raise ValueError(f"research runtime callable origin mismatch: {name}.{label}")
                if encoded not in expected_code.get(declaration, set()):
                    raise ValueError(
                        f"research runtime code differs from declaration: {name}.{label}"
                    )
            entry = (
                label,
                encoded.hex(),
                _constant(function.__defaults__),
                _constant(function.__kwdefaults__),
                _constant(_closure(function)),
            )
            module_code.update(repr(entry).encode())
            actual_code.update(f"{name}:{label}\0".encode())
            actual_code.update(repr(entry).encode())
        records[name] = {
            "path": expected.relative_to(RESEARCH_ROOT).as_posix(),
            "source_sha256": hashlib.sha256(source).hexdigest(),
            "code_sha256": module_code.hexdigest(),
            "observed_generated_methods": generated_count,
        }
    for qualified_name, value in bindings.items():
        module_name, name = qualified_name.rsplit(".", 1)
        module = modules.get(module_name)
        if module is None or getattr(module, name, None) is not value:
            raise ValueError(f"research runtime callable binding mismatch: {qualified_name}")
    return {
        "runtime_identity_version": 2,
        "runtime_origins_verified": True,
        "runtime_modules": records,
        "required_runtime_modules": sorted(required),
        "runtime_code_sha256": actual_code.hexdigest(),
        "python_cache_tag": sys.implementation.cache_tag,
        "python_version": sys.version,
        "python_optimize": sys.flags.optimize,
        "standard_wrapper_sources": wrapper_sources,
    }


def require_runtime_identity(recorded: Mapping[str, Any], current: Mapping[str, Any]) -> None:
    """Refuse legacy or mismatched research evidence before calibration reuse.

    The deterministic required module inventory includes generated code observed
    at the reviewed freeze. Compare it as well as complete source digests and the
    declared runtime contract. A documentation-only Git commit may differ.
    """
    stable_fields = (
        "runtime_identity_version",
        "runtime_origins_verified",
        "python_cache_tag",
        "python_version",
        "python_optimize",
        "standard_wrapper_sources",
        "reviewed_engine_verified",
        "engine_release_commit",
        "engine_release_contract_sha256",
        "reviewed_runtime_source_sha256",
        "reference_configuration",
        "source_only_engine_paths",
        "engine_sha256",
        "tool_sha256",
        "required_runtime_modules",
        "runtime_modules",
        "runtime_code_sha256",
        "rules_profile",
        "training_policy",
        "audit_runner",
    )
    if (
        type(recorded.get("runtime_identity_version")) is not int
        or recorded.get("runtime_identity_version") != 2
        or recorded.get("runtime_origins_verified") is not True
        or recorded.get("reviewed_engine_verified") is not True
        or any(recorded.get(key) != current[key] for key in stable_fields)
    ):
        raise ValueError(
            "review slate runtime identity differs; regenerate/review before calibration"
        )
