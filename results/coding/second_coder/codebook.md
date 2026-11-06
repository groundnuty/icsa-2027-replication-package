# Cause codebook

Give each run ONE primary code. Optionally list secondary codes (other codes that also apply).
When several apply, the primary is the first in this order.

- **infra_failure** (precedence 0): The attempt ended by a failure outside the agent's control (campaign rule: record.infra_failure).
- **output_cap** (precedence 1): The last reply stopped on the provider's output-length limit (Termination.OUTPUT_CAP). Added to the issue's table: the harness has this termination and it is not a token budget.
- **run_error** (precedence 1): The run ended in a harness or model error that is not an infra failure (Termination.ERROR). Added to the issue's table for the same reason.
- **time_cap** (precedence 1): The run ended at the wall-clock cap (Termination.TIME_CAP).
- **token_budget** (precedence 1): The run ended because it exceeded the token budget (Termination.TOKEN_BUDGET).
- **turn_cap** (precedence 1): The run ended at the turn cap (Termination.TURN_CAP).
- **truncated_listing** (precedence 2): The directory listing stopped short of the directory size (a page with is_last=false whose continuation was never requested), and the run read no data file beyond the names it was listed (a run that did has escaped the truncation: it is coded by the other rules and flagged recovered_from_truncated_listing). Attribution: `client` when no listing request carried a page token (the client returned a first page and never asked for more; also the default when the agent's own code stopped after one page, which the request log cannot tell apart); `agent` when a request carried a token and paging still stopped.
- **wrong_subset_baseline** (precedence 3): As wrong_subset_period, for the baseline part: baseline days missing as whole days, target intact, other days read or analysed instead.
- **wrong_subset_period** (precedence 3): The required target days are missing as whole days (every required cell of the day), the baseline is intact, and the run read or analysed other days outside the required set in their place (at least as many as the missing days).
- **wrong_subset_region** (precedence 4): All required data was read, and the analysed extent misses the same cells on every required day of both parts (a cell pattern, which includes all cells): the analysis covered a different region. Analysed units outside the instance's box are not representable, so a fully empty analysed extent over fully read data also lands here.
- **skipped_or_partial_read** (precedence 5): Required files (S1) or chunks (S2) were never read, or only their header was. Same rule for every option: 'never read' covers 'never downloaded' under D. Sub-case truncated_downloads (D): a download was cut short (fewer bytes than the file holds).
- **read_not_used** (precedence 6): Required data is in the read extent but not in the analysed extent, in a shape that is not one of the wrong_subset shapes.
- **early_stop** (precedence 7): The agent ended with its final message, hit no cap, and the required extent was not analysed, with no more specific rule above resolving it (includes an unfinished run whose output file was never valid, and a run whose read extent was not observed).
- **analysis_error_on_covered_data** (precedence 8): The analysed extent covers the required one, the run finished, and the result is wrong (correct == False): the computation discrepancy of #13.
- **unknown** (precedence 9): No rule resolves the case, or there is no evidence to apply one.

Secondary-only flag: `malformed_tool_calls` (a tool round had unparseable arguments).
