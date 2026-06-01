from enum import Enum
from pydantic import BaseModel, Field, model_validator


class StakeholderSource(str, Enum):
    EXPLICIT = "explicit"
    INFERRED = "inferred"


class InfluenceLevel(str, Enum):
    HIGH = "High"
    MEDIUM = "Medium"
    LOW = "Low"


class InterestLevel(str, Enum):
    HIGH = "High"
    MEDIUM = "Medium"
    LOW = "Low"


class CommunicationFrequency(str, Enum):
    WEEKLY = "Weekly"
    BI_WEEKLY = "Bi-weekly"
    MONTHLY = "Monthly"
    AD_HOC = "Ad-hoc"


class StakeholderMapEntry(BaseModel):
    name: str
    source: StakeholderSource
    rationale: str | None = Field(
        default=None,
        description="Required if source is inferred, must be empty/null if explicit",
    )
    department: str
    role_in_project: str
    influence_level: InfluenceLevel
    interest_level: InterestLevel
    engagement_strategy: str
    key_concerns: str
    communication_frequency: CommunicationFrequency
    engagement_approach: str
    communication_method: str

    @model_validator(mode="after")
    def validate_source_rationale(self) -> "StakeholderMapEntry":
        if self.source == StakeholderSource.INFERRED:
            if not self.rationale or not self.rationale.strip():
                raise ValueError("rationale is required when stakeholder is inferred")
        elif self.source == StakeholderSource.EXPLICIT:
            if self.rationale and self.rationale.strip():
                raise ValueError("rationale must be empty or null when stakeholder is explicit")
        return self


class StakeholderMap(BaseModel):
    stakeholders: list[StakeholderMapEntry] = Field(default_factory=list)
