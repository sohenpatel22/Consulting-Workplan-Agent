from enum import Enum

from pydantic import BaseModel, Field, model_validator


class RAIDCategory(str, Enum):
    RISK = "R"
    ASSUMPTION = "A"
    ISSUE = "I"
    DEPENDENCY = "D"


class RAIDItem(BaseModel):
    id: str
    category: RAIDCategory
    title: str
    description: str = ""
    severity: str = "Medium"
    owner: str = ""
    status: str = "Open"
    related_wbs_ids: list[str] = Field(default_factory=list)
    mitigation: str = ""


class RAIDLog(BaseModel):
    items: list[RAIDItem]

    @property
    def risks(self) -> list[RAIDItem]:
        return [i for i in self.items if i.category == RAIDCategory.RISK]

    @property
    def assumptions(self) -> list[RAIDItem]:
        return [i for i in self.items if i.category == RAIDCategory.ASSUMPTION]

    @property
    def issues(self) -> list[RAIDItem]:
        return [i for i in self.items if i.category == RAIDCategory.ISSUE]

    @property
    def dependencies(self) -> list[RAIDItem]:
        return [i for i in self.items if i.category == RAIDCategory.DEPENDENCY]

    @model_validator(mode="after")
    def validate_counts(self) -> "RAIDLog":
        if len(self.risks) < 3:
            raise ValueError("RAID log must contain at least 3 risks.")
        if len(self.assumptions) < 2:
            raise ValueError("RAID log must contain at least 2 assumptions.")
        return self
