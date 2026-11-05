# Knowledge plane (#6)

MCP tools for discovery and metadata, identical in every option, not written for this paper: the published
`handle_4/onedata-mcp`, unmodified.

| File | Content |
|---|---|
| `pin.json` | server repo and commit, the allowed tools, and every disabled tool with its reason |
| `tools.json` | frozen names, descriptions, input/output schemas of the exposed tools, with a sha256 |
| `extent_s1.json`, `extent_s2.json` | the metadata document stored on each layout's dataset root |

**Install** (read-only clone, never edited): see `pin.json` `server.install`. `icsa.knowledge.pin.verify_pin()` refuses a clone off the pin or with local changes.

**Disabling is the server's own setting**, `ONEDATA_MCP_TOOLS=<allow-list>` (added in the pinned commit, `tool_maturity.py`), set by `icsa.knowledge.pin.server_env`, which refuses any other value. Allowed: `get_file_attributes`, `get_file_metadata` (both take a path; neither lists anything). `list_user_spaces` and `list_space_providers` are disabled too: with the admin account `list_user_spaces` returns every space it sees (other parties' names, sizes, providers), which changes over the campaign. Disabled: everything that lists a directory or returns file content (`list_children`, `list_files_recursively`, `query_by_metadata`, `query_harvester_index`, `download_file`, `grep_file_content`), every writer, and the replication/QoS/transfer/harvester tools (not discovery of the dataset). At run start `FrozenKnowledgePlane` compares the server's tool definitions with `tools.json` and fails the start on any difference.

**Extent**: stored as Onedata JSON metadata on `/<space>/s1z` (S1) and `/<space>/s2z/sst_s2.nc` (S2), read by `get_file_metadata` (no new tool). Built from #3's extent JSON by a whitelist (`icsa.knowledge.extent_meta`); no file list, no file names, no naming pattern. The layouts differ only in `layout` and `files`. Write: `uv run python -m icsa.knowledge.writer --space-id <id> --changes-log <file> [--dry-run]` (PUT on those two ids only, only when different, read back, logged).

**Equality check**: `icsa.knowledge.equality.run_check` starts each option's sandbox and the plane as a run does, sends the probes through the harness `ToolBox`, and diffs tool definitions and responses (plus calls to disabled tools, which must all be refused). The server is a stdio child of the harness, outside the sandbox: the sandbox gate cannot reach it, so the check shows that the same server returns the same answers while each option's sandbox is up, not that the sandbox is the source of the calls.
