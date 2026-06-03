from src.shared.errors import ValidationError


def require_non_empty(value: str | None, field_name: str) -> str:
    if value is None or not value.strip():
        raise ValidationError(f"{field_name} must be a non-empty string")
    return value.strip()

