"""LLM prompts for workplan agents. Edit here to tune agent behavior."""

from pathlib import Path

from pydantic import BaseModel

from workplan_agent.llm.base import schema_instruction
from workplan_agent.llm.caching import ContentBlock, cached_block, plain_block
from workplan_agent.templates.deloitte_specs import (
    format_raid_spec_for_prompt,
    format_wbs_spec_for_prompt,
)

_TEMPLATES_DIR = Path(__file__).parent / "templates"


def _load_template(filename: str) -> str:
    return (_TEMPLATES_DIR / filename).read_text(encoding="utf-8").strip()


_WBS_OUTPUT_RULES = """
## Output

Respond with a JSON object:
- work_packages: array of rows matching the Deloitte WBS table above.

Each work_packages element must use the template field names (wbs_code, wbs_element_title,
description_scope, key_deliverable, etc.). Do not emit a separate phases list.

## Generation rules

- Align elements to stated objectives and in-scope items from the brief.
- Do not include out-of-scope work.
- Link dependencies using wbs_code values that exist in the same work_packages array.
"""

_RAID_OUTPUT_RULES = """
## Output

Respond with a JSON object with exactly these keys: risks, actions, issues, decisions.
Each value is an array of objects using the field names defined for that section above.

## Generation rules

- Minimum 3 risks and 2 actions. Add issues/decisions when implied by the brief.
- Every risk and action must include wbs_links referencing wbs_code values from the WBS.
- Risks must include mitigation and probability.
- Use priority (and probability for risks): High, Moderate, or Low.
- Derive actions from brief assumptions, required client activities, and follow-ups.
- Decisions capture pending or resolved choices that affect delivery.
"""

WBS_REQUIREMENTS = format_wbs_spec_for_prompt() + _WBS_OUTPUT_RULES
RAID_REQUIREMENTS = format_raid_spec_for_prompt() + _RAID_OUTPUT_RULES

# --- Brief parser ---

BRIEF_PARSER_SYSTEM = """You are a consulting engagement analyst. Extract structured information from client briefs.

Rules:
- Do not invent scope, objectives, or constraints not implied by the brief.
- Put ambiguities, missing information, and unclear items in open_questions.
- Preserve client naming and terminology from the brief.
- Extract all objectives with clear success criteria where stated.
- Separate in-scope and out-of-scope items explicitly.
- Identify stakeholders mentioned or implied in the brief.
- When planner instructions are included, use them to prioritize emphasis (e.g. phases,
  risks, naming) but never fabricate brief facts to satisfy them."""

BRIEF_PARSER_USER = "Parse the following client brief:\n\n{brief_text}"

_USER_INSTRUCTIONS_HEADER = """## Planner instructions (from the user)

The engagement team provided the following guidance alongside the client brief.
Apply these preferences when parsing and generating artifacts when they do not
contradict explicit facts in the brief. If guidance conflicts with the brief,
follow the brief and surface the tension in open_questions (or relevant RAID items)."""


def normalize_user_prompt(user_prompt: str | None) -> str:
    if not user_prompt:
        return ""
    return user_prompt.strip()


def format_user_instructions(user_prompt: str | None) -> str:
    """Structured user guidance block; empty when no prompt provided."""
    text = normalize_user_prompt(user_prompt)
    if not text:
        return ""
    return f"{_USER_INSTRUCTIONS_HEADER}\n\n{text}"


def _append_user_instructions(body: str, user_prompt: str | None) -> str:
    instructions = format_user_instructions(user_prompt)
    if not instructions:
        return body
    return f"{body.rstrip()}\n\n{instructions}"


# --- WBS generator ---

WBS_GENERATOR_ROLE = (
    "You are a consulting project planner. Generate a Work Breakdown Structure (WBS) "
    "that conforms to the APS1049 Deloitte template structure below."
)

WBS_GENERATOR_SYSTEM = f"""{WBS_GENERATOR_ROLE}

{WBS_REQUIREMENTS}"""

WBS_GENERATOR_USER = "Generate a WBS from this parsed brief:\n\n{brief_json}"

# --- RAID generator ---

RAID_GENERATOR_ROLE = (
    "You are a consulting engagement lead. Generate a RAID log "
    "(Risks, Actions, Issues, Decisions) that conforms to the APS1049 Deloitte template below."
)

RAID_GENERATOR_SYSTEM = f"""{RAID_GENERATOR_ROLE}

{RAID_REQUIREMENTS}"""

RAID_GENERATOR_USER = """Generate a RAID log from this parsed brief and WBS.

## Parsed Brief
{brief_json}

## WBS
{wbs_json}"""

# --- Revision ---

REVISION_RULES = """You are a consulting workplan reviewer. Apply reviewer feedback to WBS and/or RAID artifacts.

Rules:
- Apply ONLY the requested changes from the feedback.
- Preserve unaffected items and IDs where possible.
- Do not remove work packages or RAID items unless feedback explicitly asks.
- Keep Deloitte template field names and section structure.
- Return the complete updated artifact(s) in the response."""

REVISION_SYSTEM = f"""{REVISION_RULES}

When revising the WBS, follow these requirements:

{WBS_REQUIREMENTS}

When revising the RAID log, follow these requirements:

{RAID_REQUIREMENTS}"""

REVISION_CONTEXT = """## Parsed Brief
{parsed_brief_json}

## Current WBS
{wbs_json}

## Current RAID
{raid_json}"""

REVISION_WBS_USER = """Revise the WBS based on reviewer feedback.

## Parsed Brief
{parsed_brief_json}

## Current WBS
{wbs_json}

## Current RAID (for context)
{raid_json}

## Reviewer Feedback
{feedback}"""

REVISION_RAID_USER = """Revise the RAID log based on reviewer feedback.

## Parsed Brief
{parsed_brief_json}

## Current WBS
{wbs_json}

## Current RAID
{raid_json}

## Reviewer Feedback
{feedback}"""

# --- Cached prompt blocks (Anthropic cache_control) ---


def _schema_block(response_model: type[BaseModel]) -> ContentBlock:
    return cached_block(schema_instruction(response_model))


def parsed_brief_block(brief_json: str) -> ContentBlock:
    return cached_block(f"## Parsed Brief\n{brief_json}")


def brief_parser_system_blocks(response_model: type[BaseModel]) -> list[ContentBlock]:
    return [cached_block(BRIEF_PARSER_SYSTEM), _schema_block(response_model)]


def wbs_generator_system_blocks(response_model: type[BaseModel]) -> list[ContentBlock]:
    return [
        plain_block(WBS_GENERATOR_ROLE),
        cached_block(WBS_REQUIREMENTS),
        _schema_block(response_model),
    ]


def raid_generator_system_blocks(response_model: type[BaseModel]) -> list[ContentBlock]:
    return [
        plain_block(RAID_GENERATOR_ROLE),
        cached_block(RAID_REQUIREMENTS),
        _schema_block(response_model),
    ]


def revision_system_blocks(response_model: type[BaseModel]) -> list[ContentBlock]:
    static = f"{REVISION_RULES}\n\n{WBS_REQUIREMENTS}\n\n{RAID_REQUIREMENTS}"
    return [cached_block(static), _schema_block(response_model)]


def brief_parser_user_blocks(
    brief_text: str,
    user_prompt: str | None = None,
) -> list[ContentBlock]:
    body = _append_user_instructions(
        BRIEF_PARSER_USER.format(brief_text=brief_text),
        user_prompt,
    )
    return [plain_block(body)]


def wbs_generator_user_blocks(
    brief_json: str,
    user_prompt: str | None = None,
) -> list[ContentBlock]:
    task = _append_user_instructions(
        "Generate a Work Breakdown Structure (WBS) from the parsed brief above.",
        user_prompt,
    )
    return [parsed_brief_block(brief_json), plain_block(task)]


def raid_generator_user_blocks(
    brief_json: str,
    wbs_json: str,
    user_prompt: str | None = None,
) -> list[ContentBlock]:
    task = _append_user_instructions(
        "Generate a RAID log from the parsed brief and WBS above.",
        user_prompt,
    )
    return [
        parsed_brief_block(brief_json),
        plain_block(f"## WBS\n{wbs_json}\n\n{task}"),
    ]


def revision_user_blocks(
    task: str,
    parsed_brief_json: str,
    wbs_json: str,
    raid_json: str,
    feedback: str,
) -> list[ContentBlock]:
    context = REVISION_CONTEXT.format(
        parsed_brief_json=parsed_brief_json,
        wbs_json=wbs_json,
        raid_json=raid_json,
    )
    return [
        cached_block(context),
        plain_block(f"{task}\n\n## Reviewer Feedback\n{feedback}"),
    ]
