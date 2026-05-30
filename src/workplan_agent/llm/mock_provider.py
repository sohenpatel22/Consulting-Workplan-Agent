import copy
import re
from typing import TypeVar

from pydantic import BaseModel

from workplan_agent.llm.caching import LLMMessage, flatten_content
from workplan_agent.llm.fixtures import FIXTURES, RAID_FIXTURE, WBS_FIXTURE
from workplan_agent.models.raid import RAIDLog
from workplan_agent.models.wbs import WBS

T = TypeVar("T", bound=BaseModel)

_WBS_DETAIL_SUFFIX = (
    " Expanded per review: additional tasks, acceptance criteria, and dependency notes documented."
)
_RAID_DETAIL_SUFFIX = (
    " Expanded per review: impact analysis, triggers, and mitigation steps documented in detail."
)


class MockLLMProvider:
    """Returns deterministic fixture data for offline tests and demos."""

    def __init__(self) -> None:
        self.call_log: list[type[BaseModel]] = []

    def warm_prompt_cache(self) -> None:
        return

    def warm_wbs_build_prefix(self, parsed_brief_json: str) -> None:
        return

    def warm_raid_build_prefix(self, parsed_brief_json: str, wbs_json: str) -> None:
        return

    def call_structured(
        self,
        messages: list[LLMMessage],
        response_model: type[T],
    ) -> T:
        self.call_log.append(response_model)
        user_text = "\n".join(
            flatten_content(m["content"])
            for m in messages
            if m["role"] == "user"
        )

        if "Revise the WBS" in user_text:
            return self._mock_wbs_revision(user_text, response_model)
        if "Revise the RAID" in user_text:
            return self._mock_raid_revision(user_text, response_model)

        fixture = FIXTURES.get(response_model)
        if fixture is None:
            raise ValueError(f"No mock fixture for {response_model.__name__}")
        return response_model.model_validate(fixture)

    def _extract_feedback(self, user_text: str) -> str:
        match = re.search(r"## Reviewer Feedback\n(.+)", user_text, re.DOTALL)
        if match:
            return match.group(1).strip()
        return ""

    def _wants_add(self, feedback: str) -> bool:
        lower = feedback.lower()
        return any(
            word in lower
            for word in ("add ", "add a", "new ", "create ", "include a new", "append")
        )

    def _mock_wbs_revision(self, user_text: str, response_model: type[T]) -> T:
        if response_model is not WBS:
            raise ValueError(f"Expected WBS revision, got {response_model.__name__}")
        feedback = self._extract_feedback(user_text)
        data = copy.deepcopy(WBS_FIXTURE)

        wp_ids = re.findall(r"\b(\d+\.\d+)\b", feedback)
        updated = False
        for wp_id in wp_ids:
            for wp in data["work_packages"]:
                if wp["wbs_code"] == wp_id:
                    wp["description_scope"] = (wp.get("description_scope") or "") + _WBS_DETAIL_SUFFIX
                    updated = True

        if not updated:
            for wp in data["work_packages"]:
                if wp["level"] == 2:
                    wp["description_scope"] = (wp.get("description_scope") or "") + _WBS_DETAIL_SUFFIX
                    break

        if self._wants_add(feedback):
            data["work_packages"].append(
                {
                    "wbs_code": "3.3",
                    "level": 2,
                    "parent_wbs_code": "3.0",
                    "wbs_element_title": "Additional scope (per review)",
                    "description_scope": "New work package added from reviewer request."
                    + _WBS_DETAIL_SUFFIX,
                    "key_deliverable": "Review deliverable",
                    "owner": "Tech Lead",
                    "estimated_duration": "2 weeks",
                    "dependencies": ["3.2"],
                }
            )

        return response_model.model_validate(data)

    def _mock_raid_revision(self, user_text: str, response_model: type[T]) -> T:
        if response_model is not RAIDLog:
            raise ValueError(f"Expected RAID revision, got {response_model.__name__}")
        feedback = self._extract_feedback(user_text)
        data = copy.deepcopy(RAID_FIXTURE)

        item_ids = re.findall(r"\b([RADI]\d+)\b", feedback, re.IGNORECASE)
        item_ids = [i.upper() for i in item_ids]

        def _touch(section: str, item_id: str) -> bool:
            for item in data.get(section, []):
                if item["id"].upper() == item_id:
                    item["description"] = (item.get("description") or "") + _RAID_DETAIL_SUFFIX
                    return True
            return False

        updated = any(_touch("risks", i) or _touch("actions", i) for i in item_ids)

        if not updated and data.get("risks"):
            data["risks"][0]["description"] = (
                data["risks"][0].get("description") or ""
            ) + _RAID_DETAIL_SUFFIX

        if self._wants_add(feedback):
            next_r = len(data["risks"]) + 1
            data["risks"].append(
                {
                    "id": f"R{next_r}",
                    "title": "Additional risk (per review)",
                    "description": "New risk added from reviewer request." + _RAID_DETAIL_SUFFIX,
                    "priority": "Moderate",
                    "probability": "Moderate",
                    "owner": "Engagement Manager",
                    "status": "Open",
                    "wbs_links": ["3.0"],
                    "mitigation": "Track in weekly steering committee",
                }
            )

        return response_model.model_validate(data)
