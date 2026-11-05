# Environment

## To check the results

- Python 3.12 or newer (`pyproject.toml`), with the dependencies locked in `uv.lock`; `uv sync` installs them.
- `make` and a POSIX shell.
- No network after `uv sync`, no data platform, no model endpoint, no container runtime.

`make verify` needs only the Python standard library.

## What the study ran on

- **Agents.** Each run was one agent session in its own sandbox: a container built from `sandbox/Dockerfile` (base image pinned by digest,
  requirements pinned in `sandbox/requirements.txt`), or, on HPC nodes, the same image unpacked and run by `hpc_sandbox/` without a container daemon.
  `sandbox/INTERFACE.md` specifies what the sandbox enforces.
- **Models.** Seven models: two Claude models through the Anthropic API, and five open-weight models served by vLLM on GPU nodes and by a second hosted
  endpoint for the same models; the backend of each run is recorded with the run. Settings per model are in `config/models.toml`.
- **Data platform.** A Onedata deployment holding the dataset in both layouts at one site, read directly from that site's provider; M+ replicated the
  data to a second site. Platform names are replaced by site labels (`VERIFICATION.md`).
- **Hosts.** Run hosts were virtual machines and HPC nodes; the campaign recorded the environment of every run (the `hpc` stratum is reported apart in the
  analysis). Host names, addresses and accounts are not part of the package.

The harness and its configuration are described in `docs/harness.md` and `config/harness.toml`.
