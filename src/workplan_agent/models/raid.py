from typing import Any, Self

from pydantic import AliasChoices, BaseModel, Field, field_validator, model_validator

from workplan_agent.raid_sanitize import strip_mitigation_duplicate_actions

_RATING_LEVELS = frozenset({"High", "Moderate", "Low"})
_LEVEL_SCORE = {"very low": 1, "low": 2, "moderate": 3, "high": 4}
_RESPONSE_BY_RATING = {
    "High": "Monitor closely",
    "Moderate": "Monitor",
    "Low": "Respond as required",
}


def derive_risk_rating(probability: str, impact: str) -> str:
    prob_score = _LEVEL_SCORE.get(probability.strip().lower(), 2)
    impact_score = _LEVEL_SCORE.get(impact.strip().lower(), 2)
    combined = (prob_score + impact_score) / 2
    if combined >= 3.5:
        return "High"
    if combined >= 2.5:
        return "Moderate"
    return "Low"


def response_priority_for_rating(rating: str) -> str:
    return _RESPONSE_BY_RATING.get(rating, "Monitor")


class RiskEntry(BaseModel):
    id: str
    title: str
    description: str = ""
    status: str = "Open"
    mitigation: str = ""
    owner: str = ""
    owner_side: str = Field(
        default="Joint",
        description="Client, Consultant, or Joint owner side for this RAID item",
        validation_alias=AliasChoices("owner_side", "responsible_side", "company_side"),
    )
    wbs_links: list[str] = Field(
        default_factory=list,
        validation_alias=AliasChoices("wbs_links", "related_wbs_ids"),
    )
    probability: str = "Moderate"
    impact: str = Field(
        default="Moderate",
        validation_alias=AliasChoices("impact", "severity"),
    )
    risk_rating: str = ""
    risk_appetite: str = "Moderate"
    priority: str = Field(
        default="Monitor",
        description="Response level: Monitor closely, Monitor, Stay informed, or Respond as required",
    )

    model_config = {"populate_by_name": True}

    @model_validator(mode="before")
    @classmethod
    def _migrate_legacy_priority(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data
        priority = data.get("priority")
        if isinstance(priority, str) and priority in _RATING_LEVELS and "impact" not in data:
            migrated = dict(data)
            migrated["impact"] = priority
            probability = str(migrated.get("probability", "Moderate"))
            migrated.setdefault("risk_rating", derive_risk_rating(probability, priority))
            migrated.setdefault("risk_appetite", "Moderate")
            migrated["priority"] = response_priority_for_rating(str(migrated["risk_rating"]))
            return migrated
        return data

    @model_validator(mode="after")
    def _fill_derived_risk_fields(self) -> Self:
        if not self.risk_rating:
            object.__setattr__(
                self,
                "risk_rating",
                derive_risk_rating(self.probability, self.impact),
            )
        if self.priority in _RATING_LEVELS:
            object.__setattr__(
                self,
                "priority",
                response_priority_for_rating(self.risk_rating),
            )
        return self


class ActionEntry(BaseModel):
    id: str
    title: str
    description: str = ""
    status_update: str = ""
    status: str = "Open"
    owner: str = ""
    owner_side: str = Field(
        default="Joint",
        description="Client, Consultant, or Joint owner side for this RAID item",
        validation_alias=AliasChoices("owner_side", "responsible_side", "company_side"),
    )
    wbs_links: list[str] = Field(
        default_factory=list,
        validation_alias=AliasChoices("wbs_links", "related_wbs_ids"),
    )
    priority: str = Field(
        default="Moderate",
        validation_alias=AliasChoices("priority", "severity"),
    )

    model_config = {"populate_by_name": True}


class IssueEntry(BaseModel):
    id: str
    title: str
    description: str = ""
    resolution: str = ""
    owner: str = ""
    owner_side: str = Field(
        default="Joint",
        description="Client, Consultant, or Joint owner side for this RAID item",
        validation_alias=AliasChoices("owner_side", "responsible_side", "company_side"),
    )
    priority: str = Field(
        default="Moderate",
        validation_alias=AliasChoices("priority", "severity"),
    )

    model_config = {"populate_by_name": True}


class DecisionEntry(BaseModel):
    id: str
    title: str
    description_justification: str = Field(
        default="",
        validation_alias=AliasChoices("description_justification", "description"),
    )
    resolution: str = ""
    owner: str = ""
    owner_side: str = Field(
        default="Joint",
        description="Client, Consultant, or Joint owner side for this RAID item",
        validation_alias=AliasChoices("owner_side", "responsible_side", "company_side"),
    )
    priority: str = Field(
        default="Moderate",
        validation_alias=AliasChoices("priority", "severity"),
    )

    model_config = {"populate_by_name": True}


_LEGACY_CATEGORY = {
    "R": "risks",
    "A": "actions",
    "I": "issues",
    "D": "decisions",
}


class RAIDLog(BaseModel):
    risks: list[RiskEntry]
    actions: list[ActionEntry]
    issues: list[IssueEntry] = Field(default_factory=list)
    decisions: list[DecisionEntry] = Field(default_factory=list)

    @field_validator("risks", "actions", mode="before")
    @classmethod
    def _default_required_sections(cls, value: object) -> object:
        return value if value is not None else []

    @model_validator(mode="before")
    @classmethod
    def _migrate_legacy_items(cls, data: Any) -> Any:
        if not isinstance(data, dict) or "items" not in data:
            return data
        if any(key in data for key in ("risks", "actions", "issues", "decisions")):
            return data

        buckets: dict[str, list[dict[str, Any]]] = {
            "risks": [],
            "actions": [],
            "issues": [],
            "decisions": [],
        }
        for item in data.get("items", []):
            if not isinstance(item, dict):
                continue
            category = str(item.get("category", "")).upper()
            key = _LEGACY_CATEGORY.get(category)
            if key is None:
                continue
            migrated = dict(item)
            if category == "D":
                migrated["description_justification"] = migrated.pop("description", "")
            buckets[key].append(migrated)

        return {
            "risks": buckets["risks"],
            "actions": buckets["actions"],
            "issues": buckets["issues"],
            "decisions": buckets["decisions"],
        }

    @model_validator(mode="after")
    def _remove_mitigation_duplicate_actions(self) -> Self:
        cleaned = strip_mitigation_duplicate_actions(self.actions, self.risks)
        if cleaned != self.actions:
            object.__setattr__(self, "actions", cleaned)
        return self

    @property
    def items(self) -> list[RiskEntry | ActionEntry | IssueEntry | DecisionEntry]:
        """Flattened view for callers that iterate all RAID entries."""
        return [*self.risks, *self.actions, *self.issues, *self.decisions]
