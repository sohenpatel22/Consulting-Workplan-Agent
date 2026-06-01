from pydantic import BaseModel, Field


class StakeholderMapEntry(BaseModel):
    name: str
    role: str
    influence: str = Field(default="Medium", description="High, Medium, or Low power/influence")
    interest: str = Field(default="Medium", description="High, Medium, or Low interest")
    engagement_strategy: str = Field(
        default="Keep Informed",
        description="Manage Closely, Keep Satisfied, Keep Informed, or Monitor",
    )
    key_concerns: str = Field(default="", description="Key concerns, interests, or expectations")
    communication_channel: str = Field(default="", description="Preferred communication channel")
    frequency: str = Field(default="", description="Frequency of communications (e.g. Weekly, Monthly, Ad-hoc)")


class StakeholderMap(BaseModel):
    stakeholders: list[StakeholderMapEntry] = Field(default_factory=list)
