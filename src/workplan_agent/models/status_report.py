from pydantic import BaseModel, Field


class WeeklyStatusMilestone(BaseModel):
    name: str
    target_date: str
    actual_date: str | None = Field(default=None, description="Actual date completed, if applicable")
    status: str = Field(
        default="Not Started",
        description="Must be one of: Not Started, In Progress, Completed, Delayed",
    )


class WeeklyStatusReport(BaseModel):
    project_name: str
    project_manager: str
    date: str = Field(description="Week ending date or date of status report")
    summary: str = Field(description="High-level summary of status")
    new_initiatives: list[str] = Field(default_factory=list, description="New initiatives / activities started")
    blockers: list[str] = Field(default_factory=list, description="Project blockers derived from RAID or WBS")
    risks: list[str] = Field(default_factory=list, description="Key project risks derived from RAID")
    milestones: list[WeeklyStatusMilestone] = Field(default_factory=list, description="Project milestones tracking")
    supporting_links: list[str] = Field(default_factory=list, description="Supporting document or artifact links")
