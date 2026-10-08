from dataclasses import dataclass, asdict
from datetime import datetime, timezone
import hashlib
import json
from typing import Dict, Any


def validate_split(split_b: float) -> None:
    if not 0 < split_b < 1:
        raise ValueError("Treatment traffic split must be between 0 and 1.")


def assign_variant(
    lead_id: str,
    experiment_id: str,
    split_b: float = 0.10,
) -> str:
    """
    Deterministic random-looking sticky assignment.

    The same lead + experiment always maps to the same bucket.
    """
    validate_split(split_b)
    key = f"{experiment_id}:{lead_id}".encode("utf-8")
    digest = hashlib.sha256(key).hexdigest()
    bucket = int(digest[:16], 16) / float(16**16)
    return "B" if bucket < split_b else "A"


@dataclass
class ExperimentConfig:
    experiment_id: str
    name: str
    control_prompt: str
    treatment_prompt: str
    split_b: float = 0.10
    alpha: float = 0.01
    min_per_arm: int = 1000
    max_looks: int = 5
    primary_metric: str = "meeting_fixed"
    secondary_metric: str = "call_duration_sec"

    def __post_init__(self):
        validate_split(self.split_b)
        if self.min_per_arm < 1:
            raise ValueError("min_per_arm must be positive.")
        if self.max_looks < 1:
            raise ValueError("max_looks must be positive.")

    @property
    def planned_per_look_alpha(self) -> float:
        # Conservative Bonferroni correction across planned looks.
        return 0.05 / self.max_looks

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data["planned_per_look_alpha"] = self.planned_per_look_alpha
        return data


class AuditLog:
    def __init__(self):
        self.events = []

    def add(self, event: str, details: Dict[str, Any]):
        self.events.append(
            {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "event": event,
                "details": details,
            }
        )

    def as_json(self) -> str:
        return json.dumps(self.events, indent=2)
