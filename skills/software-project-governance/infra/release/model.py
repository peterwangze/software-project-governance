"""Small, dependency-free result model used by release checks."""

from dataclasses import dataclass, field
from typing import Any, Dict, List


VALID_STATES = {"PASS", "FAIL", "UNKNOWN", "BLOCKED"}


@dataclass
class CheckResult:
    state: str
    issues: List[str] = field(default_factory=list)
    facts: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.state not in VALID_STATES:
            raise ValueError(f"unsupported result state: {self.state}")

    @property
    def passed(self) -> bool:
        return self.state == "PASS"

    def as_dict(self) -> Dict[str, Any]:
        return {
            "state": self.state,
            "pass": self.passed,
            "issues": list(self.issues),
            **self.facts,
        }
