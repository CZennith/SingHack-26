"""Protected atomic writes for validated generated JSON artifacts."""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
GENERATED_OUTPUT_ROOT = PROJECT_ROOT / "outputs"
PROTECTED_ROOTS = (
    PROJECT_ROOT / "data",
    PROJECT_ROOT / "db",
    PROJECT_ROOT / "tests" / "fixtures",
)


class OutputWriteError(OSError):
    """A generated artifact could not be written safely."""


class OutputExistsError(OutputWriteError):
    """The destination exists and overwrite permission was not supplied."""


class UnsafeOutputTarget(OutputWriteError):
    """The destination would write into a protected location."""


def _reject_nonstandard_json_constant(value: str) -> None:
    raise ValueError(f"non-standard JSON constant {value}")


def _inside(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
    except ValueError:
        return False
    return True


def _checked_target(target: Path, output_root: Path) -> tuple[Path, Path]:
    resolved_target = Path(target).resolve()
    resolved_root = Path(output_root).resolve()
    if resolved_target.suffix.lower() != ".json":
        raise UnsafeOutputTarget(f"generated output must be a .json file: {resolved_target}")
    if not _inside(resolved_target, resolved_root):
        raise UnsafeOutputTarget(f"output target is outside the configured output root {resolved_root}: {resolved_target}")
    for protected_root in PROTECTED_ROOTS:
        if _inside(resolved_target, protected_root.resolve()):
            raise UnsafeOutputTarget(f"generated output may not be written under protected path {protected_root}: {resolved_target}")
    if _inside(resolved_target, PROJECT_ROOT) and not _inside(resolved_target, GENERATED_OUTPUT_ROOT.resolve()):
        raise UnsafeOutputTarget(
            f"generated output inside the repository must be written under {GENERATED_OUTPUT_ROOT}: {resolved_target}"
        )
    return resolved_target, resolved_root


def atomic_write_json(
    target: Path,
    serialized_json: str,
    *,
    output_root: Path,
    overwrite: bool = False,
    artifact_description: str,
) -> Path:
    """Atomically write already-serialized JSON under an authorized root.

    JSON is parsed before directories or temporary files are created. If any
    later step fails, the temporary file is removed and an existing target is
    left unchanged.
    """
    try:
        payload = json.loads(serialized_json, parse_constant=_reject_nonstandard_json_constant)
    except (TypeError, ValueError) as exc:
        raise OutputWriteError(f"refusing to write invalid JSON for {artifact_description}: {exc}") from exc
    if not isinstance(payload, dict):
        raise OutputWriteError(f"refusing to write non-object JSON for {artifact_description}")

    resolved_target, _ = _checked_target(Path(target), Path(output_root))
    if resolved_target.exists() and not overwrite:
        raise OutputExistsError(
            f"output already exists at {resolved_target} for {artifact_description}; "
            "use --overwrite if replacement is intentional"
        )
    resolved_target.parent.mkdir(parents=True, exist_ok=True)
    temporary_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=resolved_target.parent,
            prefix=f".{resolved_target.name}.",
            suffix=".tmp",
            delete=False,
        ) as handle:
            temporary_path = Path(handle.name)
            handle.write(serialized_json)
            handle.flush()
            os.fsync(handle.fileno())
        if resolved_target.exists() and not overwrite:
            raise OutputExistsError(
                f"output already exists at {resolved_target} for {artifact_description}; "
                "use --overwrite if replacement is intentional"
            )
        os.replace(temporary_path, resolved_target)
        temporary_path = None
    except Exception:
        if temporary_path is not None and temporary_path.exists():
            temporary_path.unlink()
        raise
    return resolved_target
