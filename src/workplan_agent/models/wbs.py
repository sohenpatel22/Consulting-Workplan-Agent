from pydantic import AliasChoices, BaseModel, Field, field_validator, model_validator


class WorkPackage(BaseModel):
    """One row in the Deloitte WBS table."""

    level: int = Field(ge=1, le=3)
    wbs_code: str = Field(validation_alias=AliasChoices("wbs_code", "id"))
    parent_wbs_code: str | None = Field(
        default=None,
        validation_alias=AliasChoices("parent_wbs_code", "parent_id"),
    )
    wbs_element_title: str = Field(
        validation_alias=AliasChoices("wbs_element_title", "name"),
    )
    description_scope: str = Field(
        default="",
        validation_alias=AliasChoices("description_scope", "description"),
    )
    key_deliverable: str = Field(
        default="",
        validation_alias=AliasChoices("key_deliverable", "deliverables"),
    )
    owner: str = Field(default="", validation_alias=AliasChoices("owner", "owner_role"))
    estimated_duration: str = ""
    dependencies: list[str] = Field(default_factory=list)

    @field_validator("key_deliverable", mode="before")
    @classmethod
    def _coerce_deliverable(cls, value: object) -> object:
        if isinstance(value, list):
            return value[0] if value else ""
        return value

    model_config = {"populate_by_name": True}


class WBS(BaseModel):
    work_packages: list[WorkPackage]

    @property
    def phases(self) -> list[str]:
        return [wp.wbs_element_title for wp in self.work_packages if wp.level == 1]

    @model_validator(mode="after")
    def validate_hierarchy(self) -> "WBS":
        l1 = [wp for wp in self.work_packages if wp.level == 1]
        if len(l1) < 3:
            raise ValueError("WBS must have at least 3 level-1 work packages.")

        for parent in l1:
            children = [
                wp
                for wp in self.work_packages
                if wp.level == 2 and wp.parent_wbs_code == parent.wbs_code
            ]
            if len(children) < 2:
                raise ValueError(
                    f"Level-1 work package '{parent.wbs_code}' must have at least 2 level-2 children."
                )

        codes = {wp.wbs_code for wp in self.work_packages}
        for wp in self.work_packages:
            if wp.parent_wbs_code and wp.parent_wbs_code not in codes:
                raise ValueError(
                    f"Work package '{wp.wbs_code}' references unknown parent "
                    f"'{wp.parent_wbs_code}'."
                )
            for dep in wp.dependencies:
                if dep not in codes:
                    raise ValueError(
                        f"Work package '{wp.wbs_code}' references unknown dependency '{dep}'."
                    )

        return self
