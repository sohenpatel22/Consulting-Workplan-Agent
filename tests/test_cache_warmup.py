from workplan_agent.llm.cache_warmup import raid_build_cache_blocks, wbs_build_cache_blocks


def test_wbs_build_cache_blocks_match_generator_layout() -> None:
    brief = '{"client_name": "Acme"}'
    _system, user = wbs_build_cache_blocks(brief)
    assert user[0]["text"] == f"## Parsed Brief\n{brief}"
    assert "cache_control" in user[0]
    assert user[1]["text"] == "Reply with OK."
    assert "cache_control" not in user[1]


def test_raid_build_cache_blocks_include_wbs_section() -> None:
    brief = '{"client_name": "Acme"}'
    wbs = '{"work_packages": []}'
    _system, user = raid_build_cache_blocks(brief, wbs)
    assert "## WBS" in user[1]["text"]
    assert wbs in user[1]["text"]
    assert "cache_control" in user[0]
