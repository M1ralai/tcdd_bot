import os
from pathlib import Path


def clean_env_value(value):
    """Strip wrapping quotes and inline comments that are outside quotes."""
    in_single_quote = False
    in_double_quote = False

    for index, char in enumerate(value):
        if char == "'" and not in_double_quote:
            in_single_quote = not in_single_quote
        elif char == '"' and not in_single_quote:
            in_double_quote = not in_double_quote
        elif (
            char == "#"
            and not in_single_quote
            and not in_double_quote
            and (index == 0 or value[index - 1].isspace())
        ):
            value = value[:index]
            break

    return value.strip().strip('"').strip("'")


def load_env():
    """Load .env values without overriding variables already provided by the shell/container."""
    env_paths = [
        Path.cwd() / ".env",
        Path(__file__).resolve().parent / ".env",
        Path(__file__).resolve().parent.parent / ".env",
    ]

    for env_path in env_paths:
        if not env_path.exists():
            continue

        for raw_line in env_path.read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue

            key, value = line.split("=", 1)
            key = key.strip()
            if not key or os.getenv(key):
                continue

            os.environ[key] = clean_env_value(value)
        return


def require_env(key):
    value = os.getenv(key)
    if value is None or value == "":
        raise RuntimeError(f"{key} env degiskeni zorunlu. .env dosyasina ekle/doldur.")
    return value


def require_env_int(key):
    value = require_env(key)
    try:
        return int(value)
    except ValueError as exc:
        raise RuntimeError(f"{key} env degiskeni sayi olmali.") from exc
