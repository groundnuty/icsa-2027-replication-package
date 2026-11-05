"""The calibration matrix runs ONCE: no run is added, re-run or swapped after results are seen.

`Ledger` is a JSON file next to the results. `claim` registers the planned matrix (its id and sha)
and refuses a second claim in the same ledger, whether for the same config (a re-run) or another
(an extension or re-draw). `begin_run` / `finish_run` track each planned run: a finished run cannot
be run again, and a run outside the plan cannot be started. Every result row carries the matrix id
and sha. The ledger file is meant to be committed with the results; the code cannot stop someone
deleting it, which is why the sha is also stamped into every result.

A failed run is an infrastructure failure, not an added run (science, #2, 2 Nov): it gets a replacement, from the same matrix
row and seed, as a fresh attempt with its own run key, up to MAX_ATTEMPTS in all and before any cell is scored. Nothing from a
failed attempt is scored; its window stays in attribution, so its reads do not move to a neighbour. A run that fails all its
attempts stays lost and leaves its cell incomplete.
"""
from __future__ import annotations

import dataclasses
import datetime as _dt
import hashlib
import json
import os
from pathlib import Path
from typing import Sequence

from .matrix import PlannedRun


MAX_ATTEMPTS = 3
RERUN = "rerun"        # a finished run of the old site_g, to be run again on the final head (science, #34, 3 Nov); its earlier record is kept and reported apart


class MatrixRefused(RuntimeError):
    """Re-running, extending or replacing a claimed calibration matrix."""


@dataclasses.dataclass(frozen=True)
class MatrixClaim:
    matrix_id: str
    sha: str
    config: tuple
    planned: tuple = ()          # every planned run's sid: a cell's verdict needs its whole allocation


def matrix_sha(plan: Sequence[PlannedRun]) -> str:
    h = hashlib.sha256()
    for r in plan:
        h.update(f"{r.order}|{r.scenario.sid}|{r.scenario.master_seed}|{r.scenario.params}\n".encode())
        if getattr(r, "masking", None) is not None:      # the sealed per-run verdict is part of what is claimed
            h.update((json.dumps(r.masking.as_dict(), sort_keys=True) + "\n").encode())
    return h.hexdigest()


class Ledger:
    def __init__(self, path: Path) -> None:
        self.path = Path(path)

    def _read(self) -> dict:
        return json.loads(self.path.read_text()) if self.path.exists() else {}

    def _write(self, d: dict) -> None:
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(json.dumps(d, indent=1, sort_keys=True))
        os.replace(tmp, self.path)

    def claim(self, plan: Sequence[PlannedRun], config: tuple) -> MatrixClaim:
        d = self._read()
        if d:
            same = d["sha"] == matrix_sha(plan)
            raise MatrixRefused(f"ledger {self.path.name} already holds matrix {d['matrix_id']}; "
                                + ("re-running it" if same else "a different matrix would extend or replace it")
                                + " is refused: the matrix runs once")
        sha = matrix_sha(plan)
        c = MatrixClaim(sha[:12], sha, config, tuple(r.scenario.sid for r in plan))
        self._write({"matrix_id": c.matrix_id, "sha": sha, "config": list(map(str, config)),
                     "planned": [r.scenario.sid for r in plan], "state": {}})
        return c

    def claimed(self) -> MatrixClaim:
        d = self._read()
        if not d:
            raise MatrixRefused("no matrix claimed in this ledger")
        return MatrixClaim(d["matrix_id"], d["sha"], tuple(d["config"]), tuple(d.get("planned", ())))

    def begin_run(self, sid: str) -> None:
        d = self._read()
        if sid not in d.get("planned", []):
            raise MatrixRefused(f"{sid} is not in the claimed matrix: runs are not added after the claim")
        st = d["state"].get(sid)
        n = self._attempts_of(d, sid)
        if st is not None and not ((str(st).startswith("lost") and n < MAX_ATTEMPTS) or str(st).startswith(RERUN)):
            raise MatrixRefused(f"{sid} was already started ({st}): every planned run is run once; only a lost run gets a "
                                f"replacement, at most {MAX_ATTEMPTS} attempts in all")
        d["state"][sid] = "started"
        d.setdefault("attempts", {})[sid] = n + 1
        self._write(d)

    def finish_run(self, sid: str) -> None:
        d = self._read()
        if d.get("state", {}).get(sid) != "started":
            raise MatrixRefused(f"{sid} was not started (or already finished)")
        d["state"][sid] = "done"
        self._write(d)

    def mark_lost(self, sid: str, reason: str) -> None:
        """A started run that did not finish (crash, infra, a short read): lost, and replaced while attempts remain (`pending`)."""
        d = self._read()
        if d.get("state", {}).get(sid) != "started":
            raise MatrixRefused(f"{sid} is not in the started state")
        d["state"][sid] = f"lost: {reason}"
        self._write(d)

    def unstart(self, sid: str, reason: str) -> None:
        """A run refused before any sandbox started (a quarantine in force): no attempt was used (science, #2, 2 Nov 08:15Z: an attempt is a
        sandbox started). The attempt count goes back, the run is pending again, and the refusal is counted in `refusals`."""
        d = self._read()
        if d.get("state", {}).get(sid) != "started":
            raise MatrixRefused(f"{sid} is not in the started state")
        n = self._attempts_of(d, sid) - 1
        d.setdefault("attempts", {})[sid] = max(0, n)
        if n <= 0 and sid in d.get("reruns", {}):
            d["state"][sid] = f"{RERUN}: {d['reruns'][sid]['reason']}"        # still the run to be done again, not a run never started
        elif n <= 0:
            del d["state"][sid]
        else:
            d["state"][sid] = f"lost: an earlier attempt; the last was refused before a sandbox started ({reason})"
        d.setdefault("refusals", {})[sid] = d.get("refusals", {}).get(sid, 0) + 1
        self._write(d)

    def rerun(self, sid: str, reason: str) -> None:
        """Science, #34, 3 Nov: every finished run of the old site_g is run again, whatever it showed, so the primary table is one VM and one head; the old record is
        kept and reported apart. The matrix, its sha and its planned list are NOT touched: only this run's state moves, from done to `rerun`, with its attempt count
        back to none. The rerun is a fresh attempt with a key of its own (calibrate.attempt_key skips the old run's directory), so nothing of the old run is
        overwritten, and the old record stays among the attempts for attribution. Only a done run with a single attempt: more would leave no key for the rerun."""
        d = self._read()
        if sid not in d.get("planned", []):
            raise MatrixRefused(f"{sid} is not in the claimed matrix")
        if d.get("state", {}).get(sid) != "done":
            raise MatrixRefused(f"{sid} is not done ({d.get('state', {}).get(sid)}): only a finished run is run again")
        n = self._attempts_of(d, sid)
        if n > 1:
            raise MatrixRefused(f"{sid} has {n} attempts already: a rerun would have no run key of its own left")
        d["state"][sid] = f"{RERUN}: {reason}"
        d.setdefault("attempts", {})[sid] = 0
        d.setdefault("reruns", {})[sid] = {"reason": reason, "of_attempts": n,
                                           "utc": _dt.datetime.now(_dt.timezone.utc).isoformat(timespec="seconds")}
        self._write(d)

    def rerun_sids(self) -> list[str]:
        """Every run that was put back for a rerun, in the plan's order: their earlier records are reported apart."""
        d = self._read()
        return [s for s in d.get("planned", []) if s in d.get("reruns", {})]

    def rerun_pending(self) -> list[str]:
        d = self._read()
        return [s for s in d.get("planned", []) if str(d.get("state", {}).get(s, "")).startswith(RERUN)]

    @staticmethod
    def _attempts_of(d: dict, sid: str) -> int:
        """A ledger from before attempts were counted holds one attempt per run with a state."""
        return d.get("attempts", {}).get(sid, 1 if sid in d.get("state", {}) else 0)

    def attempts(self, sid: str) -> int:
        return self._attempts_of(self._read(), sid)

    def note_partial_score(self, n_pending: int) -> None:
        """Replacements run before any cell is scored; a score taken earlier on request stays on the record."""
        d = self._read()
        d.setdefault("partial_scores", []).append({"utc": _dt.datetime.now(_dt.timezone.utc).isoformat(timespec="seconds"),
                                                   "n_pending": n_pending})
        self._write(d)

    def lost(self) -> list[str]:
        d = self._read()
        return [s for s, v in d.get("state", {}).items() if str(v).startswith("lost")]

    def pending(self) -> list[str]:
        d = self._read()
        return [s for s in d.get("planned", []) if s not in d["state"] or str(d["state"][s]).startswith(RERUN)
                or (str(d["state"][s]).startswith("lost") and self._attempts_of(d, s) < MAX_ATTEMPTS)]
