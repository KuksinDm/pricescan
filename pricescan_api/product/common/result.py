from dataclasses import dataclass
from typing import Any, Dict, Generic, Optional, TypeVar

T = TypeVar("T")


@dataclass(frozen=True)
class Result(Generic[T]):
    ok: bool
    value: Optional[T] = None
    error: Optional[str] = None

    @classmethod
    def success(cls, value: T) -> "Result[T]":
        return cls(ok=True, value=value)

    @classmethod
    def failure(cls, error: str) -> "Result[T]":
        return cls(ok=False, error=error)

    def to_dict(self) -> Dict[str, Any]:
        # для возврата из Celery-тасков
        return {"ok": self.ok, "value": self.value, "error": self.error}
