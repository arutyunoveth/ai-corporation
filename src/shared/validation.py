import hashlib
import json

from src.shared.errors import ValidationError


def require_non_empty(value: str | None, field_name: str) -> str:
    if value is None or not value.strip():
        raise ValidationError(f"{field_name} must be a non-empty string")
    return value.strip()


def require_non_negative(value: int, field_name: str) -> int:
    if value < 0:
        raise ValidationError(f"{field_name} must be >= 0")
    return value


def compute_payload_hash(payload_json: dict) -> str:
    normalized = json.dumps(payload_json, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def require_same_reference(expected: str, actual: str, field_name: str) -> None:
    if expected != actual:
        raise ValidationError(f"{field_name} does not match the referenced object")


def require_non_empty_list(values: list, field_name: str) -> list:
    if not values:
        raise ValidationError(f"{field_name} must not be empty")
    return values


def require_positive_number(value: float | int, field_name: str) -> float | int:
    if value <= 0:
        raise ValidationError(f"{field_name} must be > 0")
    return value
