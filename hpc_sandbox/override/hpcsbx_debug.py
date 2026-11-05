"""A pytest plugin for this host only (-p hpcsbx_debug): when a test fails, print what the stand-in knows of every container then (state, exit code, the tail of its stderr)."""
import json
import os
import subprocess

import pytest


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    out = yield
    rep = out.get_result()
    if rep.when == "call" and rep.failed:
        lines = []
        for n in subprocess.run(["docker", "ps", "-a", "--format", "{{.Names}}"], capture_output=True, text=True).stdout.split():
            ins = subprocess.run(["docker", "inspect", n], capture_output=True, text=True).stdout
            try:
                st = json.loads(ins)[0]["State"]
            except (ValueError, IndexError):
                st = {"unreadable": ins[:100]}
            err = subprocess.run(["docker", "logs", n], capture_output=True, text=True).stderr[-300:]
            lines.append(f"  {n}: running={st.get('Running')} status={st.get('Status')} exit={st.get('ExitCode')} finished={st.get('FinishedAt')} err={err!r}")
            if not n.endswith("-gate") and st.get("Running"):
                x = subprocess.run(["docker", "exec", n, "sh", "-c", "echo LD_PRELOAD=$LD_PRELOAD CONNECT=$ICSA_PM_CONNECT; grep -v localhost /etc/hosts"], capture_output=True, text=True, timeout=60)
                lines.append("     agent: " + x.stdout.replace("\n", " | ")[:300] + x.stderr[:200])
            nets = {k: v.get("IPAddress") for k, v in (json.loads(ins)[0].get("NetworkSettings", {}).get("Networks", {}) or {}).items()} if ins.strip().startswith("[") else {}
            lines.append(f"     networks: {nets}")
        rep.sections.append(("hpcsbx containers at the failure", "\n".join(lines)))
