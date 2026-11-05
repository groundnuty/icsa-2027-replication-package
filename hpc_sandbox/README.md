# HPC sandbox runners: the campaign's sandbox on site-a compute nodes

The sandbox harness (`icsa/sandbox/`, `icsa/harness/real_sandbox.py`) drives **Docker** and **sudo**. A site-a compute node has no Docker, no root, no loop devices, no user or network
namespaces (`max_user_namespaces = max_net_namespaces = 0`), `hidepid` on `/proc` (so no Apptainer *instances*), and a user cannot bind a port below 1024. This directory makes the
harness run there **without changing a byte under `icsa/`** (the snapshot's code walk, `snapshot/codecheck.py`, must stay equal to main's): a `docker` and a `sudo` program first on
`PATH`, two wrappers (`mkfs.ext4`, `journalctl`), an `LD_PRELOAD`, and a small Python override, all outside the walk, in the way `icsa/campaign/boverride.py` is.

Tested on node node_1 (job job_1), Rocky 9.8, kernel 5.14, Apptainer 1.5.4. Python 3.12 from uv; the shims themselves run under the system Python 3.9.

## What stands in for what

| the harness asks for | here |
|---|---|
| `docker image inspect -f '{{.Id}}'` of the pinned image | `images.json`: the OCI manifest digest of the campaign's archive (what `pins.json` pins), checked at build time against `pins.json` |
| `docker run -d` of the gate | a supervisor (`hpcsbx/supervisor.py`) runs `apptainer exec --containall` on a SIF of the image and keeps its log, exit code and times (`docker logs`, `inspect`) |
| `docker run -d ... sleep infinity` (the agent) | one long-lived container whose command is an **exec server** (`hpcsbx/execd.py`), run by the supervisor like the gate, with the record's binds, environment, /tmp and /dev/shm |
| `docker exec -i -u -w ... timeout -s KILL N python -` | a client of that server over a unix socket (`dockercli.exec_via_server`): the cell is a child of the server in the container's one pid namespace, in a session of its own; stdin, stdout, stderr and the exit status (128+N for a signal) pass through; a client that dies leaves the cell running |
| the kernel's OOM kill at `--memory` | the supervisor samples the container's processes ten times a second and, over the limit, kills the single process with the most anon+shmem (never the container's command), counting `oom`/`oom_kill` for the synthetic cgroup |
| `docker network create --internal`, `connect`, `inspect` | bookkeeping. The subnet the harness picks decides the sandbox's address: `10.200.a.b/28` is `127.200.a.(b+2)` for the gate |
| the agent's `--add-host name:gate_ip` | a per-container `/etc/hosts`, bound over the image's |
| quota disks: `mkfs.ext4` + `sudo mount -o loop` | `mkfs.ext4` wrapper (`-E root_owner`) + `fuse2fs` (the sudo stand-in turns `mount -o loop` into it); the FUSE directory is bound into the container |
| `--tmpfs /tmp:size=N`, `--shm-size N` | fuse2fs filesystems of those sizes (`Sandbox._check_capacity` measures `statvfs` from inside and refuses a sandbox that could hold a copy of the data) |
| port 443 of the gate | `portmap/portmap.so` (`LD_PRELOAD`): the gate's `bind()` goes to its own loopback address, ports below 1024 plus 20000; the agent's `connect()` to its gate's address on a port below 1024 goes to port plus 20000. Nothing else is touched |
| `sudo kill/cp/find/cat/rm/mv/chown` | run as the user (a chown to another uid is a no-op: cells run as the one uid there is) |
| `journalctl -u earlyoom` | empty, readable: "a host without earlyoom" in the harness's words. Any other journalctl is the real one |
| a container's cgroup (`memory.events`, `memory.peak`, `memory.stat`, `cgroup.procs`) | `override/hpcsbx_override.py` replaces four reads (`teardown._cgroup_procs`, `Sandbox._cgroup_dir`, `_other_cgroup_dir`, `_oom_counters_of`) with `hpcsbx/synthcg.py`, see below |

A container's processes are found by **pid-namespace inode** (`hpcsbx/procs.py`), learned once from a per-start environment marker (`HPCSBX_CID=<container>:<token>`, in the environment of the container's command), not by a marker a cell could drop with `env={}`.
The kernel reuses inode numbers when a namespace dies, so a recorded number is believed only while no process in it carries another container's marker.

**Why one long-lived container per sandbox, and not one `apptainer exec` per cell** (this was the first design and it was wrong): the tracer names its per-process files and start markers by `os.getpid()` and opens its streams for append, so two cells that both had pid 12 in
fresh namespaces would have merged their coverage data, and `runner._record_problem` turns "N cells ran, the tracer started in M of them" into an infrastructure error (retried, never counted). One pid namespace for the sandbox's life gives unique pids, as Docker does.

## Departures from the Docker sandbox (every run record carries them as `hpc_sandbox`)

1. **No network isolation.** Every container shares the node's network. The gate is the only route the agent's *configured* names take, but an agent cell can reach the internet and the provider directly.
2. **No kernel limits** on memory, cpu, pids or open files (the operator accepts none; `ulimit -Hn` is 51200 here, below the 1,048,576 the harness asks for). The memory limit is enforced by the supervisor at 10 Hz (a spike inside 0.1 s is not caught).
3. **No cgroup per container.** `memory.stat` is the sum of RSS of the container's processes, `memory.peak` the highest sum the supervisor saw (10 Hz),
   `memory.max` is `max`, `cpu.stat` is absent (`cpu_s` unknown). `memory.events` says `oom 0, oom_kill 0` only while Slurm's own cgroup of the step (and those above it up to the job)
   has seen no OOM kill since the container was made; if one has, the file is withheld, the harness reads that as "not known whether a process was killed", and retries the run.
4. **Cells run as the host user**, not uid 10001. The exec server is a process a cell could kill (on Docker the container's init is protected from signals sent inside it); killing it ends the container and the next `exec` is refused as "not running".
5. **Byte counters are unknown** (`between_sites_rx`, `registered_rx` are `None`): with no network namespace the interface counters would be the node's.
6. **No earlyoom.** Memory kills are the kernel's, inside Slurm's step cgroup.
7. The container's start is Apptainer's (about 0.7 s, the SIF mounted by `squashfuse`); a cell's start is not (it is a fork of the exec server). A Python start with the tracer is about 2 s on the node.
9. Disk space: fuse2fs holds back 10% of every image: writes stop at the reported `f_bavail` (measured 5 Nov: ENOSPC at 99.9% of the f_bavail, 89.0% of f_blocks). The WORK image is built 1/0.9 larger (`bin/mkfs.ext4`) so `statvfs` offers what the harness meant; the trace disk, /tmp and /dev/shm are NOT: their writable space is ~10% below the size asked for (trace 959 MB of 1 GiB against 1,050 MB on a VM; recorded in `sandbox.writable_capacity_bytes`).
8. **M (oneclient FUSE mount) does not work yet:** it needs `bind` mounts with propagation (root) and a FUSE mount with `allow_other` (`user_allow_other` is not set in `/etc/fuse.conf`).

10. The agent's environment carries four variables Docker's does not: `HPCSBX_CID`, `LD_PRELOAD=/opt/hpcsbx/portmap.so`, `ICSA_PM_OFFSET`, `ICSA_PM_CONNECT` (the port mapper). Its `/proc` shows the exec server beside its own processes.

## Constraints that shaped it

* Scratch (`/net/scratch/site-bb/user_1/user_1`) has an **inode quota**: 1,000,000 files, within 30,000 of the limit when this was built, and the quota is not this lane's. The environment (tens of thousands of files)
  lives on the node's tmpfs (`/tmp/hpcsbx-<uid>`), rebuilt from `uv.lock` or unpacked from one tgz; only single large files (SIFs, tgz) go to scratch.
* Apptainer 1.5.4 cannot read the campaign's archive (a layer with `etc/shadow` owned `root:42`: "expected blob size 3407, but only wrote ..."), so `ociunpack.py` unpacks the layers as a user,
  checking each layer's sha256 against its diff id, and `apptainer build` makes the SIF from the tree. The image's own `Env`, `WorkingDir` are kept in `images.json` and applied on every run and exec.

## Runbook: a provider's dispatcher on a node (the B form, 5 Nov)

Order (all from the lead's host, `bash hpc_ctl.sh ...` runs things in tmux on login01; a held job's step lives only as long as its `srun` client there):
1. `bash deploy.sh <job>`: the stand-ins and the venv `.pth` (verified in a clean child, a grandchild, without the variable, and the exit-87 path). `bash ship_tree.sh <clean worktree of d867010d> <job>`: the stamped tree. `bash setup_mcp.sh` on the node once (pinned onedata-mcp clone + venv at `$HPCSBX_HOME/ref/onedata-mcp`).
2. `python3 gen_hpc_launch.py --out-dir DIR [--early-cut A,B]`: the 21 B-form launch files. `bash stage_provider.sh <provider> DIR/<provider>.json [plan.keys.json]`: ONE tgz per provider on scratch (launch, slot map, service map, plan, empty endpoints file).
3. `bash hpc_ctl.sh pool <job> <agents> <gates> <node-cpus>`: idle Slurm steps, one per agent slot (17586 MiB, 4 cores of its own by affinity) and per gate slot (1035 MiB). Slots needed on a node = the sum of its dispatchers' starting levels (4 each, no live check to raise them).
4. `bash hpc_ctl.sh dispatch <job> <provider>`: start_dispatcher.sh in a step (stages files, copies the passwords and keys from `$SCRATCH/site-r/hpc-secrets` into mode-700/600 tmpfs, HOME on tmpfs so `~/.agent-framework/keys/.../lk` resolves, a config copy that differs from the tree's `harness.toml` in the Anthropic key path only, `HPCSBX_OVERRIDE=1 HPCSBX_POOL=1`, then `python -m icsa.campaign run --config ... --root ... --sandbox-image ... --past-pilot`).
5. `bash hpc_ctl.sh export <job> <provider>`: per finished attempt `<run key>__<attempt dir>.tar` (absolute path inside) + `.tar.sha256` under `$SCRATCH/site-r/hpc/<provider>/runs/`, and `state.sqlite.tar` (+ `.sha256`) by `VACUUM INTO` every 10 min; the node's copy of an attempt is removed only after the archive is read back and counted (`--prune`).
Never wrap a dispatcher in `guarded.sh` (it kills one process group and would orphan the sandboxes). `SIGTERM` to a dispatcher stops dispatch and it joins its runs.

## The HPC block's open-model sessions (5 Nov): allocator, seats, endpoints files

The block as a whole may hold only so many sessions of each open model (the lead's table, `allocator/limits.json` on scratch, edited live with `hpc_ctl.sh limits FILE`). Every dispatcher starts at cap 0 (the launch files say so) and
`hpc_caps_allocator.py` (tmux `alloc` on login01, every 90 s) raises them through the project's own `caps-set`: site-b sessions as a budget per model, **site-a slots as seats** (a seat = the slot's name in the dispatcher's own
endpoints file + `site-a_slot_caps[key]` = 1). Rules, all tested offline (`test_caps_allocator.py`): budgets never exceeded (in flight and held both count); candidates are dispatchers with a free place and pending runs, longest since last served first; a dispatcher
holds one backend per model; a Coder slot is held by one dispatcher at a time; a seat is written to the seats file before the cap that uses it and removed only after the cap is lowered and nothing is in flight; the longest holder is rotated out when others wait
(its run goes on); **fail closed**: while any dispatcher cannot be read, nothing is granted. A site-a slot is usable only with a fresh view (the HPC agent's `llm-serve/hpc/slots.json`, 180 s), `up`, a check < 150 s old, the model's pinned checkpoint revision
(`pin` in limits.json), and only for dispatchers in `site-a_providers` (those restarted with their own endpoints file and proven). `hpc_endpoints.py` (tmux `ep-<job>`, one per node) writes each dispatcher's endpoints file: exactly its seats, entries unchanged,
**a bare JSON list** (the executor iterates it as a list: `harness/slots.py` SlotPool.from_file; the campaign's own reader also takes `{"slots": [...]}`, and the first version of this loop wrote that and killed every site-a run at start with a TypeError, which the
harness-error guard turned into a stop of two models on four dispatchers, 5 Nov ~03:08Z; `test_caps_allocator.py` now parses the files with the executor's reader when `ICSA_SRC` is set), `[]` when the view is stale or unreadable, `up` false for a slot that does not answer /health from the node.
A harness-error stop is cleared only by a release file, someone's word (`b/<provider>/HARNESS_ERROR_RELEASE`, one model name per line): not written by the lane without the lead's word.
`hpc_rolling_restart.py` restarts dispatchers (a launch file is read at start) in waves when idle, with the wave excluded from grants meanwhile.

## One sandbox = one Slurm step (HPCSBX_POOL=1)

A compute node cannot start a step (srun there fails: the Slurm plugin needs libjson-c.so.4), so `pool_launcher.py` keeps idle steps alive from the login node and `hpcsbx/pool.py` hands a container's command to a free one (`hpcsbx/stepd.py`, over a unix socket on node tmpfs; the environment goes through a mode-0600 file, never an argument). The command then runs in that step's cgroup:
the kernel enforces `memory.max` (99% of `--mem`: 18,255,851,520 B for an agent, main's 18,253,611,008 B; 1.07 GB for a gate), and the harness reads the step's own `memory.events`, `memory.peak`, `memory.stat` and `cpu.stat`
(linked into the directory it reads; `cgroup.procs` is built from the pid namespace). An OOM kill is the kernel's, counted in `memory.events`, classified `memory_limit`; the container goes on. CPU: every overlapping step otherwise gets cores 0-3, so
stepd pins its command by `sched_setaffinity` to 4 cores of the slot's own (an affinity, not a quota; a cell could widen it). A step that ends is replaced by a fresh one (fresh cgroup and counters). Without the pool (`HPCSBX_POOL` unset) the userspace 10 Hz guard applies.

## Isolation: what an agent cell can and cannot do (live-tested, `smoke_isolation.py`)

It holds `ONEDATA_TOKEN` (the harness's own design: the gate holds no token; Docker's internal network was the barrier). Here: `portmap.so` is loaded into every dynamically linked process through `/etc/ld.so.preload` and reads a read-only config file, so clearing the environment does not
drop it; the agent's `connect()`/`sendto()`/`sendmsg()` may go only to its own gate address, loopback (except the provider's ports 8443/30443, `HPCSBX_DENY_PORTS`) and AF_UNIX, every other destination fails ENETUNREACH; `/etc/resolv.conf` is empty. Results: a direct provider read with the token, a connect to the node's IP and to 198.51.100.4, and a DNS lookup all fail;
the gate by name works. **Not stopped:** a static binary, or a raw `connect(2)` through `syscall()` (seccomp cannot read a sockaddr; a seccomp user-notify supervisor would). The residual is stamped in every record (`sandbox.hpc_runtime.departures.network`).

## Memory: the job's cgroup, not the node

The kernel kills at the **Slurm job's** `memory.max` (285.1 GiB for job job_1 on node_1, 126.7 GiB for job job_1 on node_1), and both nodes show the whole 377 GiB node in `/proc/meminfo`,
shared with other jobs (and with other lanes' files in the node's `/tmp`: 18 GiB of `lane-snap-*` and `icsa-data` were there when this was measured). **The sandboxes' disks are tmpfs (RAM) and tmpfs pages are charged to the
cgroup that wrote them**, so work disk, trace disk, /tmp, /dev/shm and the gate's spool all count against the job. Measured at the campaign's real limits (smoke_realsize.py, `Limits.for_dataset` with S2 = 3,785,412,176 B):

| | agent memory limit | work disk | trace | /tmp + /dev/shm | gate spool | worst case in RAM |
|---|---|---|---|---|---|---|
| T, T-unpaginated | 17 GiB | 0.96 GB | 1 GiB | 0.5 + 0.06 GiB | none | about 19.5 GiB |
| D | 17 GiB | 4.54 GB (a downloaded file fills it) | 1 GiB | 0.5 + 0.06 GiB | up to the file: 3.79 GB | about 27 GiB |

A real-size D download of 3.53 GiB through a gate (mock provider) took 31 s and held **7.5 GiB of tmpfs at its peak** (the file in /work plus the gate's spool of it), 0.3 GiB after `stop`: nothing is left behind.
The dispatcher's host-memory hold (`icsa.campaign.hostmem`, launch keys `host_mem_pause_below_gib`/`host_mem_resume_at_gib`) is pointed by the override at the room left under the **job's** limit (`hpcsbx/jobmem.py`),
and `guarded.sh` trips at 90% of it (`HPCSBX_TRIP_FRAC`). A sandbox's real memory is mostly far below its limit (the naive whole-grid pattern peaked at 7.8 GiB), so the limits' sum is an overcommit here, as on the other hosts.
`HPCSBX_WORK_ROOT` moves the sandboxes' directory (default: `$ICSA_DATA/sandboxes`, node tmpfs); **scratch (Lustre) does not work for it**: fuse2fs cannot mount on a Lustre directory ("no mount appeared").

## Tested at 12 at once

`smoke_parallel.py --n 12 --rounds 2` (24 full lifecycles with the real tracer, T, T-unpaginated and D mixed, from threads of one process, `HPCSBX_TRACE=1`) on node node_1: 24 of 24 passed, all 12 started within
9.0 to 9.6 s of each other (3 s alone), no signal went to another container's process (`signals.log` checked against each target's marker), nothing left behind, the supervisors (two per sandbox) used a mean of a few percent and a peak of 157% of ONE core
in total for 24 of them.

## The dispatcher on a node (what is tested, what is not)

* `python -m icsa.campaign run --stub` starts and runs on a node under the override (`earlyoom.require_driver_exempt` passes: a host without earlyoom passes; SQLite on tmpfs; 72 stub runs in 40 s). **It refuses to start from a tree with
  no git and no `.code-stamp.json`**: `ship_tree.sh <clean git worktree> <jobid>` stamps where git is (`tools/stamp_code.py`), archives tracked files, unpacks over the node's repo keeping its venv, and syncs it.
* **This directory sits outside `tools/` on purpose:** `icsa/codestamp.py` hashes `icsa`, `config`, `protocol`, `tools`, `pyproject.toml` and `uv.lock` into the tree hash that is pinned per dispatcher and compared between hosts. The branch's
  tree hash equals main's 52ddcad8 (`bb49eee5...`); a directory under `tools/` would have changed it. On a node this directory is deployed beside the repo (`$HPCSBX_HOME/tools`), never inside it.
* **A dispatcher killed with SIGKILL (`smoke_crash.py`)**: 3 sandboxes up, `kill -9` the driver; the next `Sandbox.start` reaps the dead owner's 6 containers and 3 networks (`netpool.reap_orphans`), `reap.reap_run` collects each dead attempt's
  evidence (output, trace, gate log, file counts and bytes checked) and removes its mounts and directory; nothing is left (no container, network, mount, state directory, sandbox directory or process). Everything the stand-ins start is detached
  (own sessions), so a dead dispatcher leaves it all running until that reaper.
* **A held job's step lives as long as its `srun` client on login01.** Start the dispatcher in `tmux` on login01 (`/usr/bin/tmux` is there) with `srun --jobid=<job> --overlap ...`; if the client or login01 dies, Slurm ends the step and everything in it.
* **`export_runs.py`**: one verified tgz per finished attempt to scratch (one inode each; scratch has an inode quota), a SQLite-backup copy of the store (the store stays on tmpfs: SQLite locks do not work on Lustre), `--prune` only after
  the archive is read back and counted. Tested on the stub's 72 attempts: export, idempotent re-run, sha256 check, prune, store copy `integrity_check` ok.
* **Not tested: the real executor (`icsa.harness.run:execute_run`), the B launch form, a real provider, slot users, model endpoints, M.**

## Use

```
bash deploy.sh [jobid]                  # from the lead's host: ship this directory to the node, build portmap.so, write images.json (checks the pins)
# on the node, inside a step of a job we hold:
export HPCSBX_HOME=/tmp/hpcsbx-$(id -u) PATH=$HPCSBX_HOME/tools/bin:$PATH HPCSBX_OVERRIDE=1 PYTHONPATH=$HPCSBX_HOME/tools/override ICSA_DATA=$HPCSBX_HOME/data
$HPCSBX_HOME/repo/.venv/bin/python $HPCSBX_HOME/tools/smoke_lifecycle.py   # start, cells with the REAL tracer, pid uniqueness, a process surviving its cell, metadata, collect, stop, leftovers
bash $HPCSBX_HOME/tools/guarded.sh <command>   # any command under a tripwire on the node's memory (no kernel limit exists here; HPCSBX_TRIP_GIB, default 150)
```

`deploy.sh` also writes the venv's `.pth` (`zz_hpcsbx_override.pth`) and runs `verify_override.sh`: a clean `env -i` child and a grandchild have the override, a process without `HPCSBX_OVERRIDE=1` does not, the docker stand-in then
refuses `run`, and an install that fails ends the process with exit 87 (as boverride's does). **A dispatcher must be started with `HPCSBX_OVERRIDE=1` in its environment**; its children inherit it.

`setup_node.sh` builds the environment on a node (uv, Python 3.12, the venv from `uv.lock`, the repo tree). `HPCSBX_BUILD_AS=sandbox` lets the harness's own tests (`tests/sandbox`) run: their
`docker build` becomes an alias of the pinned image instead of a build.
