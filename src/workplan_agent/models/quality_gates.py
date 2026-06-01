from pydantic import BaseModel, Field


class QualityGateItem(BaseModel):
    category: str = Field(description="Category of check: WBS, RAID, Stakeholder, or Status")
    title: str = Field(description="Short title of the quality check")
    description: str = Field(description="Detailed instruction on what to verify")
    passed: bool = Field(default=False, description="Whether the automated check passed")
    message: str = Field(default="", description="Feedback message from automated validator")
    manual: bool = Field(default=True, description="True if it requires manual human check, False if fully automated")


class QualityGates(BaseModel):
    items: list[QualityGateItem] = Field(default_factory=list)
