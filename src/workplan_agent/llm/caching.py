"""Helpers for Anthropic prompt caching and OpenAI prefix reuse."""

from typing import Any, Literal, TypedDict

CACHE_EPHEMERAL: dict[str, str] = {"type": "ephemeral"}


class TextBlock(TypedDict, total=False):
    type: Literal["text"]
    text: str
    cache_control: dict[str, str]


ContentBlock = TextBlock
MessageContent = str | list[ContentBlock]


class LLMMessage(TypedDict):
    role: Literal["system", "user", "assistant"]
    content: MessageContent


def cached_block(text: str) -> ContentBlock:
    return {"type": "text", "text": text, "cache_control": CACHE_EPHEMERAL}


def plain_block(text: str) -> ContentBlock:
    return {"type": "text", "text": text}


def flatten_content(content: MessageContent) -> str:
    if isinstance(content, str):
        return content
    return "\n\n".join(block["text"] for block in content if block.get("type") == "text")


def count_cache_blocks(messages: list[LLMMessage]) -> int:
    total = 0
    for message in messages:
        content = message["content"]
        if isinstance(content, list):
            total += sum(1 for block in content if "cache_control" in block)
    return total


def has_cached_blocks(messages: list[LLMMessage]) -> bool:
    return count_cache_blocks(messages) > 0


MAX_CACHE_BLOCKS = 4


def system_blocks_to_api(blocks: list[ContentBlock]) -> list[dict[str, Any]]:
    return [dict(block) for block in blocks]
