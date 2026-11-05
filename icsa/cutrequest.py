"""The bound on the request a run was cut in (amendment 26(c) and (d), science #34), in tokens: one place for the spend alarm (icsa.campaign.progress,
from the attempt's run_record.json) and the scorer (from the RunRecord), so that the dollars and the report-scale tokens bound the same request.

The request that was cut is the one after the last completed turn. Its input is at most that turn's whole input, plus that turn's output (the assistant
message is sent back), plus the cap of each of that turn's tool results: `output_cap_chars` characters, at most 4 UTF-8 bytes each, one token per byte. Its
output is at most the output limit, the study's 32,768 or the model's own maximum if lower (`ModelSpec.output_tokens`). One token per byte is an assumption,
and an upper bound."""
from __future__ import annotations

TOOL_BYTES_PER_CHAR = 4      # the cap is on characters; a UTF-8 character is at most 4 bytes, and a token is counted per byte (an upper bound)


def harness_caps(model: str) -> tuple[int, int, int]:
    """(output tokens one request can ask for, characters of one tool result, tokens a run may use) from config/harness.toml and models.toml: the model's own
    maximum if lower than the study's cap (`ModelSpec.output_tokens`); a model not in models.toml has the study's cap."""
    from icsa.harness.config import ConfigError, load_config
    hc = load_config()
    try:
        out = hc.model(model).output_tokens(hc.limits.max_output_tokens)
    except ConfigError:
        out = hc.limits.max_output_tokens
    return out, hc.limits.output_cap_chars, hc.limits.token_budget


def cut_request_input(last_input: int, last_output: int, tool_calls: int, chars: int) -> int:
    """The most the request after a completed turn can carry in: that turn's input and output, and each tool call's result at its cap."""
    return last_input + last_output + tool_calls * chars * TOOL_BYTES_PER_CHAR


def of_record(record) -> tuple[int, int] | None:
    """(input, output) tokens of the bound on the request a RunRecord was cut in, or None: its usage is complete, or it was cut in its first request (no turn)."""
    if record.usage_complete or not record.turns:
        return None
    out_cap, chars, _ = harness_caps(record.run.model)
    last = record.turns[-1]
    return cut_request_input(last.input_tokens, last.output_tokens, len(last.tool_calls or []), chars), out_cap
