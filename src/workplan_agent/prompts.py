"""LLM prompts for workplan agents. Edit here to tune agent behavior."""

from pathlib import Path

from pydantic import BaseModel

from workplan_agent.llm.base import schema_instruction
from workplan_agent.llm.caching import ContentBlock, cached_block, plain_block
from workplan_agent.templates.deloitte_specs import (
    build_raid_generation_contract,
    build_stakeholder_generation_contract,
    build_status_report_generation_contract,
    build_wbs_generation_contract,
    raid_json_output_instruction,
    stakeholder_json_output_instruction,
    status_json_output_instruction,
    wbs_json_output_instruction,
)

_TEMPLATES_DIR = Path(__file__).parent / "templates"

# Deloitte template contracts (from templates/deloitte/*_template.spec.json)
WBS_REQUIREMENTS = build_wbs_generation_contract()
RAID_REQUIREMENTS = build_raid_generation_contract()
STAKEHOLDER_REQUIREMENTS = build_stakeholder_generation_contract()
STATUS_REQUIREMENTS = build_status_report_generation_contract()

# --- Brief parser ---

BRIEF_PARSER_SYSTEM = """You are a consulting engagement analyst. Extract structured information from client briefs.

Rules:
- Do not invent scope, objectives, or constraints not implied by the brief.
- Put ambiguities, missing information, and unclear items in open_questions.
- For each open question (at most four), add a matching planner_confirmations entry with
  the same question text and 2–5 tentative suggested_answers the planner might choose
  before build (concrete options implied by the brief where possible).
- Do not include overall engagement risk appetite in open_questions or
  planner_confirmations (the application adds that separately).
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


def append_generation_context(body: str, context: str | None) -> str:
    """Append pre-formatted planner guidance (instructions + confirmed answers)."""
    text = normalize_user_prompt(context)
    if not text:
        return body
    return f"{body.rstrip()}\n\n{text}"


_CONFIRMED_ANSWERS_HEADER = """## Confirmed open questions (planner sign-off)

The engagement team resolved the following ambiguities from the brief before WBS/RAID
generation. Treat each answer as a decided fact when building artifacts."""


def format_confirmed_answers(
    resolved: list[tuple[str, str]] | None,
) -> str:
    if not resolved:
        return ""
    lines = [_CONFIRMED_ANSWERS_HEADER, ""]
    for index, (question, answer) in enumerate(resolved, start=1):
        lines.append(f"{index}. **Q:** {question}")
        lines.append(f"   **A:** {answer}")
    return "\n".join(lines)


def build_generation_guidance(
    user_prompt: str | None,
    *,
    confirmed_answers: list[tuple[str, str]] | None = None,
) -> str:
    """Planner instructions plus confirmed open-question answers for WBS/RAID."""
    parts: list[str] = []
    instructions = format_user_instructions(user_prompt)
    if instructions:
        parts.append(instructions)
    confirmed = format_confirmed_answers(confirmed_answers)
    if confirmed:
        parts.append(confirmed)
    return "\n\n".join(parts)


# --- WBS generator ---

WBS_GENERATOR_ROLE = (
    "You are a consulting project planner. Produce a Work Breakdown Structure that "
    "implements the Deloitte WBS generation contract below."
)

WBS_GENERATOR_SYSTEM = f"""{WBS_GENERATOR_ROLE}

{WBS_REQUIREMENTS}

{wbs_json_output_instruction()}"""

WBS_GENERATOR_USER = "Generate a WBS from this parsed brief:\n\n{brief_json}"

# --- RAID generator ---

RAID_GENERATOR_ROLE = (
    "You are a consulting engagement lead. Produce a RAID log that implements the "
    "Deloitte RAID generation contract below."
)

RAID_GENERATOR_SYSTEM = f"""{RAID_GENERATOR_ROLE}

{RAID_REQUIREMENTS}

{raid_json_output_instruction()}"""

RAID_GENERATOR_USER = """Generate a RAID log from this parsed brief and WBS.

## Parsed Brief
{brief_json}

## WBS
{wbs_json}"""

# --- Stakeholder Map generator ---

STAKEHOLDER_GENERATOR_ROLE = (
    "You are a consulting stakeholder manager. Produce a Stakeholder Map that "
    "implements the Deloitte Stakeholder Map generation contract below."
)

STAKEHOLDER_GENERATOR_SYSTEM = f"""{STAKEHOLDER_GENERATOR_ROLE}

{STAKEHOLDER_REQUIREMENTS}

{stakeholder_json_output_instruction()}"""

STAKEHOLDER_GENERATOR_USER = """Generate a Stakeholder Map from this parsed brief, WBS, and RAID log.

## Parsed Brief
{brief_json}

## WBS
{wbs_json}

## RAID Log
{raid_json}"""

# --- Weekly Status Report generator ---

STATUS_GENERATOR_ROLE = (
    "You are an engagement manager. Produce a Weekly Status Report that "
    "implements the Deloitte Weekly Status Report generation contract below."
)

STATUS_GENERATOR_SYSTEM = f"""{STATUS_GENERATOR_ROLE}

{STATUS_REQUIREMENTS}

{status_json_output_instruction()}"""

STATUS_GENERATOR_USER = """Generate a Weekly Status Report from this parsed brief, WBS, and RAID log.

## Parsed Brief
{brief_json}

## WBS
{wbs_json}

## RAID Log
{raid_json}"""

# --- Revision ---

REVISION_RULES = """You are a consulting workplan reviewer. Apply reviewer feedback to WBS, RAID, Stakeholder Map, and/or Weekly Status Report artifacts.

Rules:
- Apply ONLY the requested changes from the feedback.
- Preserve unaffected items and IDs where possible.
- Do not remove items unless feedback explicitly asks.
- Return the complete updated artifact(s) in the response."""

REVISION_SYSTEM = f"""{REVISION_RULES}

When revising the WBS, follow this contract:

{WBS_REQUIREMENTS}

When revising the RAID log, follow this contract:

{RAID_REQUIREMENTS}"""

REVISION_STAKEHOLDER_SYSTEM = f"""{REVISION_RULES}

When revising the Stakeholder Map, follow this contract:

{STAKEHOLDER_REQUIREMENTS}

{stakeholder_json_output_instruction()}"""

REVISION_STATUS_SYSTEM = f"""{REVISION_RULES}

When revising the Weekly Status Report, follow this contract:

{STATUS_REQUIREMENTS}

{status_json_output_instruction()}"""

REVISION_CONTEXT = """## Parsed Brief
{parsed_brief_json}

## Current WBS
{wbs_json}

## Current RAID
{raid_json}

## Current Stakeholder Map
{stakeholder_map_json}

## Current Weekly Status Report
{status_report_json}"""

REVISION_WBS_USER = """Revise the WBS based on reviewer feedback.

## Parsed Brief
{parsed_brief_json}

## Current WBS
{wbs_json}

## Current RAID
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

REVISION_STAKEHOLDER_USER = """Revise the Stakeholder Map based on reviewer feedback.

## Parsed Brief
{parsed_brief_json}

## Current Stakeholder Map
{stakeholder_map_json}

## Reviewer Feedback
{feedback}"""

REVISION_STATUS_USER = """Revise the Weekly Status Report based on reviewer feedback.

## Parsed Brief
{parsed_brief_json}

## Current Weekly Status Report
{status_report_json}

## Reviewer Feedback
{feedback}"""

# --- Cached prompt blocks (Anthropic cache_control) ---


def _schema_block(response_model: type[BaseModel]) -> ContentBlock:
    return cached_block(schema_instruction(response_model))


def _wbs_output_block() -> ContentBlock:
    return cached_block(wbs_json_output_instruction())


def _raid_output_block() -> ContentBlock:
    return cached_block(raid_json_output_instruction())


def _stakeholder_output_block() -> ContentBlock:
    return cached_block(stakeholder_json_output_instruction())


def _status_output_block() -> ContentBlock:
    return cached_block(status_json_output_instruction())


def parsed_brief_block(brief_json: str) -> ContentBlock:
    return cached_block(f"## Parsed Brief\n{brief_json}")


def brief_parser_system_blocks(response_model: type[BaseModel]) -> list[ContentBlock]:
    return [cached_block(BRIEF_PARSER_SYSTEM), _schema_block(response_model)]


def wbs_generator_system_blocks(_response_model: type[BaseModel]) -> list[ContentBlock]:
    return [
        plain_block(WBS_GENERATOR_ROLE),
        cached_block(WBS_REQUIREMENTS),
        _wbs_output_block(),
    ]


def raid_generator_system_blocks(_response_model: type[BaseModel]) -> list[ContentBlock]:
    return [
        plain_block(RAID_GENERATOR_ROLE),
        cached_block(RAID_REQUIREMENTS),
        _raid_output_block(),
    ]


def stakeholder_generator_system_blocks(
    _response_model: type[BaseModel],
) -> list[ContentBlock]:
    return [
        plain_block(STAKEHOLDER_GENERATOR_ROLE),
        cached_block(STAKEHOLDER_REQUIREMENTS),
        _stakeholder_output_block(),
    ]


def status_generator_system_blocks(_response_model: type[BaseModel]) -> list[ContentBlock]:
    return [
        plain_block(STATUS_GENERATOR_ROLE),
        cached_block(STATUS_REQUIREMENTS),
        _status_output_block(),
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
    task = append_generation_context(
        "Generate a Work Breakdown Structure (WBS) from the parsed brief above.",
        user_prompt,
    )
    return [parsed_brief_block(brief_json), plain_block(task)]


def raid_generator_user_blocks(
    brief_json: str,
    wbs_json: str,
    user_prompt: str | None = None,
) -> list[ContentBlock]:
    task = append_generation_context(
        "Generate a RAID log from the parsed brief and WBS above.",
        user_prompt,
    )
    return [
        parsed_brief_block(brief_json),
        plain_block(f"## WBS\n{wbs_json}\n\n{task}"),
    ]


def stakeholder_generator_user_blocks(
    brief_json: str,
    wbs_json: str,
    raid_json: str,
    user_prompt: str | None = None,
) -> list[ContentBlock]:
    task = append_generation_context(
        "Generate a Stakeholder Map from the parsed brief, WBS, and RAID log above.",
        user_prompt,
    )
    return [
        parsed_brief_block(brief_json),
        plain_block(f"## WBS\n{wbs_json}\n\n## RAID Log\n{raid_json}\n\n{task}"),
    ]


def status_generator_user_blocks(
    brief_json: str,
    wbs_json: str,
    raid_json: str,
    user_prompt: str | None = None,
) -> list[ContentBlock]:
    task = append_generation_context(
        "Generate a Weekly Status Report from the parsed brief, WBS, and RAID log above.",
        user_prompt,
    )
    return [
        parsed_brief_block(brief_json),
        plain_block(f"## WBS\n{wbs_json}\n\n## RAID Log\n{raid_json}\n\n{task}"),
    ]


def revision_user_blocks(
    task: str,
    parsed_brief_json: str,
    wbs_json: str,
    raid_json: str,
    feedback: str,
    stakeholder_map_json: str = "{}",
    status_report_json: str = "{}",
) -> list[ContentBlock]:
    context = REVISION_CONTEXT.format(
        parsed_brief_json=parsed_brief_json,
        wbs_json=wbs_json,
        raid_json=raid_json,
        stakeholder_map_json=stakeholder_map_json,
        status_report_json=status_report_json,
    )
    return [
        cached_block(context),
        plain_block(f"{task}\n\n## Reviewer Feedback\n{feedback}"),
    ]
