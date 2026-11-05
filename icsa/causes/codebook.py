"""The cause codebook (#17): one primary code per coded run, optional secondary codes,
a fixed precedence order. The rule text lives here, next to each code, and is what the
blind coding sheet ships to the second coder.

Population (who gets a code): every finished run the instrument (#9) labels `omitting`,
every unfinished run, and every finished run whose extent is complete but whose result is
wrong (`correct == False`). Finished runs labelled `unknown` are NOT coded: they are
counted and reported (`Batch.skipped`). Complete and correct runs need no cause.

Precedence, applied in this order (the first code that fires is primary, the others that
fire are secondary):

  0. infra_failure                      the attempt was lost to the platform, nothing else matters
  1. termination: time_cap / turn_cap / token_budget / output_cap / run_error
                                        the proximate reason; the access codes below that
                                        also fire are listed as secondary
  2. truncated_listing
  3. wrong_subset_period / wrong_subset_baseline   (substitution evidence, so before skipped)
  4. wrong_subset_region
  5. skipped_or_partial_read
  6. read_not_used
  7. early_stop
  8. analysis_error_on_covered_data
  9. unknown
"""
from __future__ import annotations

import dataclasses


@dataclasses.dataclass(frozen=True)
class Code:
    name: str
    rank: int
    rule: str


CODES: tuple[Code, ...] = (
    Code("infra_failure", 0,
         "The attempt ended by a failure outside the agent's control (campaign rule: record.infra_failure)."),
    Code("time_cap", 1, "The run ended at the wall-clock cap (Termination.TIME_CAP)."),
    Code("turn_cap", 1, "The run ended at the turn cap (Termination.TURN_CAP)."),
    Code("token_budget", 1, "The run ended because it exceeded the token budget (Termination.TOKEN_BUDGET)."),
    Code("output_cap", 1,
         "The last reply stopped on the provider's output-length limit (Termination.OUTPUT_CAP). "
         "Added to the issue's table: the harness has this termination and it is not a token budget."),
    Code("run_error", 1,
         "The run ended in a harness or model error that is not an infra failure (Termination.ERROR). "
         "Added to the issue's table for the same reason."),
    Code("truncated_listing", 2,
         "The directory listing stopped short of the directory size (a page with is_last=false whose "
         "continuation was never requested), and the run read no data file beyond the names it was listed (a run that did has escaped the truncation: "
         "it is coded by the other rules and flagged recovered_from_truncated_listing). "
         "Attribution: `client` when no listing request carried a page token (the client returned a "
         "first page and never asked for more; also the default when the agent's own code stopped "
         "after one page, which the request log cannot tell apart); `agent` when a request carried "
         "a token and paging still stopped."),
    Code("wrong_subset_period", 3,
         "The required target days are missing as whole days (every required cell of the day), the "
         "baseline is intact, and the run read or analysed other days outside the required set in "
         "their place (at least as many as the missing days)."),
    Code("wrong_subset_baseline", 3,
         "As wrong_subset_period, for the baseline part: baseline days missing as whole days, "
         "target intact, other days read or analysed instead."),
    Code("wrong_subset_region", 4,
         "All required data was read, and the analysed extent misses the same cells on every required "
         "day of both parts (a cell pattern, which includes all cells): the analysis covered a "
         "different region. Analysed units outside the instance's box are not representable, so a "
         "fully empty analysed extent over fully read data also lands here."),
    Code("skipped_or_partial_read", 5,
         "Required files (S1) or chunks (S2) were never read, or only their header was. Same rule for "
         "every option: 'never read' covers 'never downloaded' under D. Sub-case truncated_downloads "
         "(D): a download was cut short (fewer bytes than the file holds)."),
    Code("read_not_used", 6,
         "Required data is in the read extent but not in the analysed extent, in a shape that is not "
         "one of the wrong_subset shapes."),
    Code("early_stop", 7,
         "The agent ended with its final message, hit no cap, and the required extent was not "
         "analysed, with no more specific rule above resolving it (includes an unfinished run whose "
         "output file was never valid, and a run whose read extent was not observed)."),
    Code("analysis_error_on_covered_data", 8,
         "The analysed extent covers the required one, the run finished, and the result is wrong "
         "(correct == False): the computation discrepancy of #13."),
    Code("unknown", 9, "No rule resolves the case, or there is no evidence to apply one."),
)

CODE_NAMES: tuple[str, ...] = tuple(c.name for c in CODES)
RANK = {c.name: c.rank for c in CODES}
RULE = {c.name: c.rule for c in CODES}

# not a cause, and set for every run (coded or not, complete ones included): the run's listings were
# truncated and it read a data file beyond the names it was listed (see rules.recovered_from_truncation)
RECOVERED_FLAG = "recovered_from_truncated_listing"

# not a cause: a flag listed among the secondary codes when the run had malformed tool calls
MALFORMED_TOOL_CALLS = "malformed_tool_calls"
SECONDARY_ONLY = (MALFORMED_TOOL_CALLS,)


def codebook_markdown() -> str:
    """The codebook as shown to a second coder."""
    out = ["# Cause codebook", "",
           "Give each run ONE primary code. Optionally list secondary codes (other codes that also apply).",
           "When several apply, the primary is the first in this order.", ""]
    for c in sorted(CODES, key=lambda c: (c.rank, c.name)):
        out += [f"- **{c.name}** (precedence {c.rank}): {c.rule}"]
    out += ["", f"Secondary-only flag: `{MALFORMED_TOOL_CALLS}` (a tool round had unparseable arguments).", ""]
    return "\n".join(out)
