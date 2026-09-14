import json
from functools import lru_cache
from pathlib import Path

COUNTRIES_PATH = Path(__file__).parent / "data" / "countries.json"


@lru_cache
def load_countries() -> list:
    return json.loads(COUNTRIES_PATH.read_text(encoding="utf-8"))


def country_by_code(code: str) -> dict:
    for c in load_countries():
        if c["code"] == code:
            return c
    raise KeyError(f"Unknown country code: {code!r}")
