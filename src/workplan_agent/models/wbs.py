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
    from_confirmed_answer: bool = Field(
        default=False,
        description="True when this row directly implements a confirmed open-question answer",
    )

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

    @model_validator(mode="before")
    @classmethod
    def _normalize_parent_codes(cls, data: object) -> object:
        """Map common LLM parent codes (e.g. '1') to phase codes ('1.0')."""
        if not isinstance(data, dict):
            return data
        packages = data.get("work_packages")
        if not isinstance(packages, list):
            return data

        l1_codes: dict[str, str] = {}
        for item in packages:
            if not isinstance(item, dict) or item.get("level") != 1:
                continue
            code = item.get("wbs_code") or item.get("id")
            if code:
                l1_codes[str(code)] = str(code)

        stem_to_l1 = {code.split(".")[0]: code for code in l1_codes}

        normalized: list[object] = []
        for item in packages:
            if not isinstance(item, dict):
                normalized.append(item)
                continue
            row = dict(item)
            parent = row.get("parent_wbs_code") or row.get("parent_id")
            if parent is not None and str(parent).strip():
                parent_str = str(parent).strip()
                if parent_str not in l1_codes:
                    if parent_str in stem_to_l1:
                        parent_str = stem_to_l1[parent_str]
                    elif f"{parent_str}.0" in l1_codes:
                        parent_str = f"{parent_str}.0"
                row["parent_wbs_code"] = parent_str
            normalized.append(row)

        return {**data, "work_packages": normalized}

