# Attributing platform-record lines to runs, under concurrency

Fault injection can run serially; the agent runs (H3: record vs labels) run concurrently, so each
record needs a key the agent cannot control. Implemented in `matcher.py`.

| record | key | how | when it fails |
|---|---|---|---|
| audit (default) | (Onedata user, UTC interval) | **one Onedata user per concurrency slot**; the scheduler records `RunInterval(run_key, option, slot, start, end)`; `slot_map.json` = `{slot: {"user": user_id, "option": T|D|M}}` (`load_slot_map`; one user per slot enforced). Each slot serves ONE option, so the user also gives the option; `attribute_audit_by_slot` raises if a run's option is not its slot's option, and `option_of_user(slot_map)` is the trusted discriminator for the option-scoped fallback. `attribute_audit_by_slot` joins on (user, widened interval) | two runs of one slot overlapping (impossible if the scheduler is right) or a slot without a user: ambiguous / error. An event from an unknown user fits no run |
| audit, **fallback** (no per-slot users) | time only | `attribute_audit_fallback`, **refused unless the caller passes `allow_unattributed=True`; calibration and the analysis never do (science, #11, 21:40Z; a test checks no module under `icsa/` passes it)**: only runs with no overlapping run in scope are matched; the rest are reported unattributable, with the covered share per option | default scope `all` (no run may overlap); scope `option` needs a trusted per-option discriminator (`option_of_event`, e.g. a user or space per option) and is refused without one |
| Traefik (T, D; switched on) | header `X-ICSA-Run: <run_key>` | added by #7's gate outside the agent container; Traefik keeps it (`--accesslog.fields.headers.names.X-ICSA-Run=keep`). `attribute_traefik_by_header` ignores client IP (shared NAT) and time; lines without the header, or with an unknown key, are dropped and counted | the gate not adding the header: every line is unattributable (the count shows it) |
| oneclient perf (M; switched on) | sidecar | one sidecar per run, so by construction; `perf_events` reads that sidecar's directory, never the newest file | missing directory: error |

Creating the per-slot users is an admin action (operator). Until the map exists, only the fallback
runs. All three are tested with hand-built overlapping concurrent runs.

## Knowledge-plane lines are excluded by construction

The knowledge plane (#6) reads attributes and metadata through the same provider and ingress as the
runs. Its lines are removed from every record before attribution, and are never counted as a run's
reads or as unattributable. Identity (configured under `"knowledge_plane"` in the slot-map file,
`load_knowledge_plane`; it may not share a user with a slot):

- audit log: its own Onedata user(s) (`users`);
- Traefik: `User-Agent` starting with `user_agent` (default `icsa-knowledge-plane/`; the pin follows);
  Traefik must keep the header (`--accesslog.fields.headers.names.User-Agent=keep`, already in the 10c flags);
- perf log: one sidecar per run, the plane has none.

Reported per run window: `Attribution.n_kp_excluded` (audit, fallback; widened window, any principal) and
`RunKeyAttribution.n_kp_excluded` / `kp_by_run` (Traefik, per window if the windows are passed). With no
`kp` given nothing is excluded, so callers must pass it.

## Each option is calibrated against its own lines (live check, 1 Nov 2026)

The audit log's request types do not tell the client (`results/faults-live/20261101T212027Z`): a REST read (T, D)
is logged as `fuse_request::file_request::open_file_with_extended_info`, `...::synchronize_block`, one
`proxyio_request::remote_read` and `...::release` per GET; an oneclient read (M, proxy I/O) as `...::open_file`, N x
`proxyio_request::remote_read` (N follows the client's read calls), `...::fsync` and `...::release`. So `remote_read`
is not unique to M and `fuse_request` does not mean oneclient. That does not matter for attribution, because a slot
user serves one option: each option's calibration and agent runs are scored on that option's own users' lines only,
never on another option's request mix. The detector's audit rule (open or read) is the same for every option.

M's oneclient does not pass the gate: its only Traefik lines are `GET /clproto` websocket upgrades, with no run key,
no file and the shared NAT client address. Traefik is not a record for M (M's switched-on record is the perf CSV).
