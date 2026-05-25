from pydantic import BaseModel, Field, model_validator


class WorkPackage(BaseModel):
    id: str
    level: int = Field(ge=1, le=3)
    parent_id: str | None = None
    name: str
    description: str = ""
    deliverables: list[str] = Field(default_factory=list)
    owner_role: str = ""
    estimated_duration: str = ""
    dependencies: list[str] = Field(default_factory=list)


class WBS(BaseModel):
    phases: list[str] = Field(
        default_factory=lambda: ["Discovery", "Design", "Build", "Transition"]
    )
    work_packages: list[WorkPackage]

    @model_validator(mode="after")
    def validate_hierarchy(self) -> "WBS":
        l1 = [wp for wp in self.work_packages if wp.level == 1]
        if len(l1) < 3:
            raise ValueError("WBS must have at least 3 level-1 work packages.")

        for parent in l1:
            children = [
                wp
                for wp in self.work_packages
                if wp.level == 2 and wp.parent_id == parent.id
            ]
            if len(children) < 2:
                raise ValueError(
                    f"Level-1 work package '{parent.id}' must have at least 2 level-2 children."
                )

        ids = {wp.id for wp in self.work_packages}
        for wp in self.work_packages:
            if wp.parent_id and wp.parent_id not in ids:
                raise ValueError(
                    f"Work package '{wp.id}' references unknown parent '{wp.parent_id}'."
                )
            for dep in wp.dependencies:
                if dep not in ids:
                    raise ValueError(
                        f"Work package '{wp.id}' references unknown dependency '{dep}'."
                    )

        return self
