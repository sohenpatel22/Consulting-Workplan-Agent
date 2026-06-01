from pydantic import BaseModel, Field


class MilestoneStatus(BaseModel):
    milestone: str
    target_date: str
    status: str = Field(default="Not Started", description="Not Started, In Progress, Completed, or Delayed")


class WeeklyStatusReport(BaseModel):
    project_title: str
    client_name: str
    reporting_period: str = Field(default="", description="Reporting period / week ending date")
    overall_status: str = Field(default="Green", description="Overall RAG status: Green, Amber, Red")
    executive_summary: str = Field(default="", description="High-level executive summary of project status")
    key_achievements: list[str] = Field(default_factory=list, description="Key achievements completed this week")
    planned_activities: list[str] = Field(default_factory=list, description="Planned key activities for next week")
    milestones: list[MilestoneStatus] = Field(default_factory=list, description="Project milestones tracking")
