from workplan_agent.llm.anthropic_provider import model_rejects_sampling_params


def test_opus_48_rejects_sampling() -> None:
    assert model_rejects_sampling_params("claude-opus-4-8")
    assert model_rejects_sampling_params("claude-opus-4-7-20260416")


def test_older_models_allow_sampling() -> None:
    assert not model_rejects_sampling_params("claude-sonnet-4-6")
    assert not model_rejects_sampling_params("claude-opus-4-20250514")
