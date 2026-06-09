from enum import Enum

from pydantic import BaseModel, Field, model_validator


class RaciLetter(str, Enum):
    RESPONSIBLE = "R"
    ACCOUNTABLE = "A"
    CONSULTED = "C"
    INFORMED = "I"


class RaciRow(BaseModel):
    activity: str = Field(description="Deliverable or activity aligned to the WBS")
    assignments: dict[str, RaciLetter] = Field(
        default_factory=dict,
        description="Role name to R/A/C/I assignment",
    )
    from_confirmed_answer: bool = Field(
        default=False,
        description="True when this row directly implements a confirmed open-question answer",
    )


class RaciMatrix(BaseModel):
    roles: list[str] = Field(
        default_factory=list,
        description="Column headers — stakeholder roles for the engagement",
    )
    rows: list[RaciRow] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_assignments(self) -> "RaciMatrix":
        role_set = set(self.roles)
        for row in self.rows:
            unknown = set(row.assignments) - role_set
            if unknown:
                raise ValueError(
                    f"assignments reference unknown roles: {', '.join(sorted(unknown))}"
                )
        return self
