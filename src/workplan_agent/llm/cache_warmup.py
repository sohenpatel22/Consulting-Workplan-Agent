"""Prime Anthropic prompt cache with the same block layout as real WBS/RAID calls."""

from __future__ import annotations

import logging
from typing import Any

from workplan_agent.llm.caching import ContentBlock, system_blocks_to_api
from workplan_agent.models.raid import RAIDLog
from workplan_agent.models.wbs import WBS
from workplan_agent.prompts import (
    parsed_brief_block,
    plain_block,
    raid_generator_system_blocks,
    wbs_generator_system_blocks,
)

logger = logging.getLogger(__name__)

_WARMUP_TAIL = "Reply with OK."


def wbs_build_cache_blocks(parsed_brief_json: str) -> tuple[list[ContentBlock], list[ContentBlock]]:
    """System + user blocks matching WBS generation (cached brief + variable task tail)."""
    system = wbs_generator_system_blocks(WBS)
    user = [
        parsed_brief_block(parsed_brief_json),
        plain_block(_WARMUP_TAIL),
    ]
    return system, user


def raid_build_cache_blocks(
    parsed_brief_json: str,
    wbs_json: str,
) -> tuple[list[ContentBlock], list[ContentBlock]]:
    """System + user blocks matching raid_generator_user_blocks layout."""
    system = raid_generator_system_blocks(RAIDLog)
    user = [
        parsed_brief_block(parsed_brief_json),
        plain_block(f"## WBS\n{wbs_json}\n\n{_WARMUP_TAIL}"),
    ]
    return system, user
