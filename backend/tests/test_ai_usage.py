from app.services.ai_usage import provider_usage


class _Provider:
    name = "example"
    model = "model"
    last_request_id = "req-123"
    last_usage = {
        "prompt_tokens": 12,
        "completion_tokens": 7,
        "total_tokens": 19,
    }


class _InputOutputProvider:
    last_request_id = None
    last_usage = {
        "input_tokens": 4,
        "output_tokens": 6,
    }


def test_provider_usage_reads_openai_compatible_token_fields():
    assert provider_usage(_Provider()) == (12, 7, 19, "req-123")


def test_provider_usage_supports_input_output_aliases_and_computes_total():
    assert provider_usage(_InputOutputProvider()) == (4, 6, 10, None)


def test_provider_usage_defaults_missing_usage_to_zero():
    class EmptyProvider:
        pass

    assert provider_usage(EmptyProvider()) == (0, 0, 0, None)
