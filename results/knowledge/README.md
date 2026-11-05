# Knowledge-plane equality check, live (#6)

Real sandboxes (`icsa.sandbox.Sandbox`, M with real oneclient `--insecure` via `campaign_data_config`), real data provider site-g,
space `icsa2027_data_20261101T090944Z`, server `handle_4/onedata-mcp` at the pinned commit (see `protocol/knowledge/pin.json`).
Tokens: sandboxes get read-only, REST- (M: oneclient-) and space-scoped tokens; the knowledge plane gets its own read-only
space-scoped token (`plane_principal` in the JSON: token id, subject, caveat types; no value). No admin token reaches any of them.
Each option: its sandbox is started, one cell runs in it, the plane is started as a run starts it, and every probe goes through the
harness `ToolBox` (tool results capped as in a run); calls to the disabled tools go straight to the server. T is run twice (control).

| layout | options | response/definition differences | volatile probes (T vs T control) | the 2 tools answered in every option | the 7 disabled tools refused in every option | tool-definition sha256 (same in all four) | UTC |
|---|---|---|---|---|---|---|---|
| S1 | T, T-unpaginated, D, M | 0 | 0 | True | True | `53616be4af86240f` | 20261101T153916Z |
| S2 | T, T-unpaginated, D, M | 0 | 0 | True | True | `53616be4af86240f` | 20261101T154204Z |

`differences` in each JSON lists every tool-definition or response difference between an option and T (empty), `volatile_probes_in_control`
lists probes whose answer changed between T and its own repeat (empty), and `observations` holds the tool definitions and the response
text per option and probe. Run with `uv run python -m icsa.knowledge.live_equality --out results/knowledge`.

The plane runs through `icsa/knowledge/serve.py` (NOT the stock onedata-mcp entrypoint: it only sets httpx's default User-Agent to `icsa-knowledge-plane/<pin short sha>`, recorded as `user_agent`). Each plane start used its own freshly minted, Onezone-examined token (`plane_token_ids`), none equal to a sandbox token (`run_token_ids`). The User-Agent on the wire is tested in `tests/knowledge/test_serve_wire.py` against a local mock.
