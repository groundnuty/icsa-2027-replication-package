#!/usr/bin/env python3
"""Keep a pool of idle Slurm steps alive in a held job (run it on the login node, in tmux): one `stepd` per slot (hpcsbx/stepd.py), restarted when its step ends.

    python3 pool_launcher.py --job job_1 --agents 16 --gates 16 [--agent-core-base 8] [--gate-cores 4-7] [--home /tmp/hpcsbx-106007] [--mem-agent-mib 17586] [--mem-gate-mib 1035]

An agent slot is a step with `--mem` 17586M (Slurm applies 99% of it, 18,255,... B: main's 16 GiB + 1 GiB tracer headroom = 18,253,611,008 B, which the harness gives Docker) and all the job's CPUs in its
cpuset (every overlapping step otherwise gets the SAME four cores); stepd pins its command to the slot's own 4 cores with sched_setaffinity (a limit by affinity, not a quota: a cell could widen it).
A gate slot has 1035M (Docker's `--memory 1g`) and the shared cores of --gate-cores. A step that ends (its sandbox is done, or it failed) is replaced after a second, with a fresh cgroup and fresh
counters; a slot that fails five times in a row waits 30 s. When the job is no longer RUNNING (squeue) the launcher ends. Python 3.6 (the login node's), standard library only.
"""
import argparse
import subprocess
import sys
import time


def job_running(job):
    try:
        out = subprocess.run(["squeue", "-h", "-j", str(job), "-o", "%T"], stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, universal_newlines=True, timeout=60).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return True                       # squeue is not answering: not known to be over
    return out == "RUNNING"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--job", required=True)
    ap.add_argument("--agents", type=int, default=0)
    ap.add_argument("--gates", type=int, default=0)
    ap.add_argument("--agent-core-base", type=int, default=8)
    ap.add_argument("--cores-per-agent", type=int, default=4)
    ap.add_argument("--gate-cores", default="4-7")
    ap.add_argument("--home", default="/tmp/hpcsbx-106007")
    ap.add_argument("--mem-agent-mib", type=int, default=17586)
    ap.add_argument("--mem-gate-mib", type=int, default=1035)
    ap.add_argument("--node-cpus", type=int, default=192, help="CPUs of the job's node: the step's cpuset (stepd then pins to the slot's cores)")
    a = ap.parse_args()
    slots = []
    for i in range(a.agents):
        lo = a.agent_core_base + i * a.cores_per_agent
        slots.append(("agent", str(i), "@%d-%d" % (lo, lo + a.cores_per_agent - 1), a.mem_agent_mib))
    for j in range(a.gates):
        slots.append(("gate", str(j), "@" + a.gate_cores, a.mem_gate_mib))
    procs = {}
    fails = {}
    last = {}
    print("pool_launcher: job %s, %d agent slots, %d gate slots" % (a.job, a.agents, a.gates), flush=True)
    while True:
        if not job_running(a.job):
            print("pool_launcher: job %s is not RUNNING: ending" % a.job, flush=True)
            for p in procs.values():
                p.terminate()
            return 0
        now = time.time()
        for kind, slot, cores, mem in slots:
            key = (kind, slot)
            p = procs.get(key)
            if p is not None and p.poll() is None:
                continue
            if p is not None:
                fails[key] = fails.get(key, 0) + 1 if now - last.get(key, 0) < 20 else 0
                if fails[key] >= 5:
                    if now - last[key] < 30:
                        continue
                    fails[key] = 0
            cmd = ["srun", "--jobid=" + a.job, "--overlap", "-N1", "-n1", "--mem=%dM" % mem, "-c", str(a.node_cpus), "--job-name=hpcsbx-%s-%s" % (kind, slot), "--quiet",
                   "python3", a.home + "/tools/hpcsbx/stepd.py", a.home, kind, slot, cores]
            procs[key] = subprocess.Popen(cmd, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            last[key] = now
            time.sleep(0.15)              # not all at once: the controller answers each step request
        time.sleep(1.0)


if __name__ == "__main__":
    sys.exit(main())
