from pathlib import Path
from typing import Any


def read_secret_file(raw_path: str, *, description: str = "Secret file", hint: str = "") -> str:
    path = Path(raw_path)
    if not path.is_file():
        raise FileNotFoundError(f"{description} not found at {path}{hint}")
    return path.read_text(encoding="utf-8").strip()


def resolve_secret(data: Any, *, key: str, hint: str = "") -> Any:
    if not isinstance(data, dict):
        return data

    raw_path: object = data.get(f"{key}_file")
    if raw_path is None:
        return data

    value: str = read_secret_file(
        str(raw_path),
        description=f"Secret file '{key}_file'",
        hint=hint,
    )
    return {**data, key: value}
