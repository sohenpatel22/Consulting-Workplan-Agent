from typing import Any

from pydantic import AliasChoices, BaseModel, Field, field_validator, model_validator


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
    priority: str = Field(
        default="Moderate",
        validation_alias=AliasChoices("priority", "severity"),
    )

    model_config = {"populate_by_name": True}


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

    @property
    def items(self) -> list[RiskEntry | ActionEntry | IssueEntry | DecisionEntry]:
        """Flattened view for callers that iterate all RAID entries."""
        return [*self.risks, *self.actions, *self.issues, *self.decisions]
