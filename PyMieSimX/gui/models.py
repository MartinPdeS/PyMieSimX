"""Typed data contracts shared by the computation and Dash layers."""

from dataclasses import dataclass
from typing import Any, Literal, Mapping, TypedDict


FieldValues = Mapping[str, Any]
MutableFieldValues = dict[str, Any]
MessageLevel = Literal["success", "warning", "error"]


class ExperimentResult(TypedDict):
    """JSON-safe result returned by a parameter-sweep computation."""

    rows: list[dict[str, Any]]
    columns: list[str]
    parameter_columns: list[str]
    measure: str
    units: dict[str, str]
    row_count: int


class SingleResult(TypedDict):
    """JSON-safe result returned by the particle explorer."""

    figure: dict[str, Any]
    summary: dict[str, str]


class JobSnapshot(TypedDict):
    """Public state of a background experiment job."""

    job_id: str
    status: str
    result: ExperimentResult | None
    error: str | None
    submitted_at: str
    started_at: str | None
    finished_at: str | None


@dataclass(frozen=True)
class ExperimentRequest:
    """Validated shape of a request crossing into the experiment service."""

    source_type: str
    source_values: FieldValues
    scatterer_type: str
    scatterer_values: FieldValues
    detector_type: str
    detector_values: FieldValues
    measure: str

    def as_kwargs(self) -> dict[str, Any]:
        """Return keyword arguments accepted by the compatibility API."""
        return {
            "source_type": self.source_type,
            "source_values": dict(self.source_values),
            "scatterer_type": self.scatterer_type,
            "scatterer_values": dict(self.scatterer_values),
            "detector_type": self.detector_type,
            "detector_values": dict(self.detector_values),
            "measure": self.measure,
        }
