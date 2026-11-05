#!/usr/bin/env bash
# The fault-injection fidelity inputs for an interim (lane-snap, #34; the lead and science, 5 Nov): fault calibration's adapter_rows.jsonl and h3_table.csv, scored on a COPY of its root.
#   fidelity_score.sh captures          bring the audit capture up to date from our incremental audit store ($V/snap-fault/captures: the root's capture files + PULLS.jsonl, refreshed in calibrate's own format)
#   fidelity_score.sh make              score a fresh COPY of the root on .23 (long: tens of minutes, one core) with those captures laid over it -> $V/snap-fault/<tag>/{adapter_rows.jsonl,h3_table.csv,capture.age.json},
#                                       $V/snap-fault/LATEST = <tag>. REFUSES (no result, LATEST unchanged) when a capture was last read before the newest run of the root ended, unless that capture is named in
#                                       FIDELITY_ALLOW_STALE (e.g. traefik.jsonl): then the result carries the staleness (capture.age.json) and the driver prints it.
#   fidelity_score.sh pull <seal dir>   copy the LATEST result into <seal>/frozen/fault/ with its age against the seal's t (seconds, in fault.age) and the captures' staleness; exit 0 only when both files are there
#   (the driver only PULLS: a score takes longer than an interim may spend; `captures` and `make` run from a loop or by hand, and once more after fault calibration's last run)
# Why captures (science, 5 Nov 06:58Z): `calibrate score` reads audit.log and traefik.jsonl in the root, which had last read site_g on 2 Nov 06:28Z, so the 934 later runs were uncovered and every audit and traefik row of
# the fidelity read n_faulted 0. The audit log is not read from site_g again: our incremental store (m-audit, every slot user, site_g's lines byte-exact, from 4 Nov 00:33:45Z on) holds them. Only the lines inside a run's own window
# (+-600 s) of the calibration's slot users are taken: the same slots carry the main campaign's runs, tens of millions of lines `score` attributes to no calibration run. The span before the store begins is not
# read: it is written into PULLS.jsonl as a gap (n_gone), which `capture_gaps` turns into `not observed on the audit record` for any run inside it, never into `unfaulted`.
# `calibrate score` reads its --out (LEDGER.json, plan.pkl, runs/, audit.log, pulls/, RUN_TAGS.json, IMAGES.json) AND writes its results into it (rows.jsonl, adapter_rows.jsonl, h3_table.*), and
# with --partial notes the partial score in LEDGER.json: so it is never run on the live root. The root's files are copied on .23 (rsync -a, the PAUSE and RUN.pid files left out) into a FRESH
# directory under /mnt/volume2/icsa-2027/lane-snap-score/ on .23, the captures laid over it, scored there with the root's own tree (wt/launch-f1c242a, its venv) under memcap 6 and nice 19, and only the result
# files are brought back. Nothing is written in the root; the copy is kept for the next run's rsync (the newest 2 are kept). stdout and stderr of `score` go to a sealed log: it prints cell verdicts.
set -u
export SSH_AUTH_SOCK=
MODE=${1:?captures|make|pull}
V=/mnt/volume2/icsa-2027
WT=~/work/wt
TREE=${TREE:-$WT/snap-interim}; PYL=${PYL:-$WT/fill-09ecc2c0/.venv/bin/python}
DOCS=${DOCS:-$V/launch}                                   # the installed copies of fidelity_audit_lines.py and fidelity_refresh.py
ROOT=$V/calibration-11-rerun-f1c242a                      # on .23
K=~/.secrets/icsa-2027/runvm_ed25519; KH=~/.secrets/icsa-2027/runvm_known_hosts
SSH23=(ssh -o BatchMode=yes -o ConnectTimeout=15 -o IdentitiesOnly=yes -i "$K" -o UserKnownHostsFile="$KH" email-1@example)
RSH="ssh -o BatchMode=yes -o ConnectTimeout=15 -o IdentitiesOnly=yes -i $K -o UserKnownHostsFile=$KH"
SF=$V/snap-fault; mkdir -p -m 700 "$SF"
if [ "$MODE" = pull ]; then
  SEAL=${2:?seal dir}; T=$(python3 -I -c "import json,sys; print(json.load(open(sys.argv[1]))['t'])" "$SEAL/out/work/cut/cut.json" 2>/dev/null || true)
  L=$(cat "$SF/LATEST" 2>/dev/null) || { echo "no fault score yet ($SF/LATEST)"; exit 1; }
  [ -s "$SF/$L/adapter_rows.jsonl" ] && [ -s "$SF/$L/h3_table.csv" ] || { echo "the latest score $L is incomplete"; exit 1; }
  OUT=$SEAL/frozen/fault; mkdir -p -m 700 "$OUT"; cp -f "$SF/$L/adapter_rows.jsonl" "$SF/$L/h3_table.csv" "$OUT/"; chmod 600 "$OUT"/*
  echo "$L" > "$OUT/fault.tag"
  age=$(python3 -I -c "import sys,datetime as dt; l=dt.datetime.strptime(sys.argv[1],'%Y%m%dT%H%M%SZ').replace(tzinfo=dt.timezone.utc).timestamp(); n=dt.datetime.now(dt.timezone.utc).timestamp(); print(int(n-l))" "$L")
  echo "fault score $L, made $age s ago" | tee "$OUT/fault.age"
  if [ -s "$SF/$L/capture.age.json" ]; then
    cp -f "$SF/$L/capture.age.json" "$OUT/"; chmod 600 "$OUT/capture.age.json"
    python3 -I -c "
import json,sys
j=json.load(open(sys.argv[1]))
print('fault captures: newest run ended', j['newest_run_end'], '|', ' | '.join(f\"{n} read the source {c['pulled_utc']}: \" + ('STALE by %d s' % c['older_than_newest_run_s'] if c['older_than_newest_run_s'] else 'covers the newest run') for n, c in j['captures'].items()))" "$OUT/capture.age.json" | tee -a "$OUT/fault.age"
  else
    echo "fault captures: staleness not recorded (this score was made before the guard)" | tee -a "$OUT/fault.age"
  fi
  exit 0
fi

if [ "$MODE" = captures ]; then
  CAP=$SF/captures; mkdir -p -m 700 "$CAP"; umask 077
  [ -f "$CAP/PULLS.jsonl" ] || rsync -a -e "$RSH" "email-1@example:$ROOT/audit.log" "email-1@example:$ROOT/traefik.jsonl" "email-1@example:$ROOT/PULLS.jsonl" "email-1@example:$ROOT/pulls" "$CAP/" \
    || { echo "captures: cannot copy the root's capture files"; exit 2; }
  # the runs' windows, from the root's own run.json files (a run with only a directory has none)
  "${SSH23[@]}" "cd $ROOT/runs && python3 -I -c '
import json, glob, sys
out = []
for f in glob.glob(\"*/run.json\"):
    d = json.load(open(f))
    out.append({\"run\": f.split(\"/\")[0], \"slot\": d.get(\"slot\"), **{k: v for k, v in d.items() if (k.endswith(\"_utc\") or k.startswith(\"token_valid\")) and isinstance(v, str)}})
json.dump(out, sys.stdout)'" > "$CAP/windows.json.tmp" && mv -f "$CAP/windows.json.tmp" "$CAP/windows.json" || { echo "captures: cannot read the runs' windows on .23"; exit 2; }
  NEWEST=$(python3 -I -c "
import json,sys,datetime as dt
e=[]
for r in json.load(open(sys.argv[1])):
    for k in ('run_end_utc','lease_end_utc'):
        if r.get(k): e.append(dt.datetime.fromisoformat(r[k]).timestamp())
print(dt.datetime.fromtimestamp(max(e), dt.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'))" "$CAP/windows.json") || exit 2
  UNTIL=$(python3 -I -c "
import sys,datetime as dt,time
n=dt.datetime.fromisoformat(sys.argv[1].replace('Z','+00:00')).timestamp()+3600
print(dt.datetime.fromtimestamp(min(n, time.time()-600), dt.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'))" "$NEWEST")
  cap_t() { (cd "$TREE" && PYTHONPATH=. PYTHONDONTWRITEBYTECODE=1 "$PYL" "$DOCS/fidelity_refresh.py" --dir "$CAP" --check) | python3 -I -c "import json,sys; print(json.load(sys.stdin).get(sys.argv[1],''))" "$1"; }
  PA=$(cap_t audit.log); PT=$(cap_t traefik.jsonl)
  [ -n "$PA" ] && [ -n "$PT" ] || { echo "captures: cannot read when the root's captures last read the source (audit '$PA', traefik '$PT')"; exit 2; }
  echo "captures: newest run ended $NEWEST; audit.log read the source $PA; traefik.jsonl read the source $PT; audit lines wanted up to $UNTIL"
  if python3 -I -c "import sys,datetime as dt; f=lambda s: dt.datetime.fromisoformat(s.replace('Z','+00:00')).timestamp(); sys.exit(0 if f(sys.argv[1])>=f(sys.argv[2]) else 1)" "$PA" "$NEWEST"; then
    echo "captures: the audit capture already covers the newest run"
  else
    COVER=$(python3 -I -c "import json,datetime as dt; j=json.load(open('$V/m-audit/backfill/capture.json')); print(dt.datetime.fromtimestamp(j['covered_from'], dt.timezone.utc).isoformat(timespec='milliseconds'))") || exit 2
    GAP=(); SINCE=()
    if python3 -I -c "import sys,datetime as dt; f=lambda s: dt.datetime.fromisoformat(s.replace('Z','+00:00')).timestamp(); sys.exit(0 if f(sys.argv[1])<f(sys.argv[2])-60 else 1)" "$PA" "$COVER"; then
      GAP=(--mark-gap-to "$COVER"); echo "captures: the incremental store begins $COVER, after the capture's last read ($PA): that span is NOT read and is marked as a gap"
    else
      SINCE=(--since "$(python3 -I -c "import sys,datetime as dt; print(dt.datetime.fromtimestamp(dt.datetime.fromisoformat(sys.argv[1].replace('Z','+00:00')).timestamp()-3600, dt.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'))" "$PA")")
    fi
    nice -n 15 "$V/bin/memcap" 3 "$PYL" "$DOCS/fidelity_audit_lines.py" --slot-map "$TREE/config/slot_map.json" --windows "$CAP/windows.json" --pad-s 600 --until "$UNTIL" "${SINCE[@]}" --out "$CAP/audit_new.lines" \
      || { echo "captures: the audit lines could not be taken from the incremental store"; exit 3; }
    (cd "$TREE" && PYTHONPATH=. PYTHONDONTWRITEBYTECODE=1 nice -n 15 "$V/bin/memcap" 6 "$PYL" "$DOCS/fidelity_refresh.py" --dir "$CAP" --name audit.log --new "$CAP/audit_new.lines" --pulled-utc "$UNTIL" "${GAP[@]}") \
      || { echo "captures: the audit capture could not be refreshed"; exit 3; }
  fi
  PT_OK=no; python3 -I -c "import sys,datetime as dt; f=lambda s: dt.datetime.fromisoformat(s.replace('Z','+00:00')).timestamp(); sys.exit(0 if f(sys.argv[1])>=f(sys.argv[2]) else 1)" "$PT" "$NEWEST" && PT_OK=yes
  echo "captures: traefik.jsonl covers the newest run: $PT_OK (a read of site_g's Traefik logs is not made here)"
  exit 0
fi

[ "$MODE" = make ] || { echo "usage: $0 captures | make | pull <seal>"; exit 64; }
TAG=$(date -u +%Y%m%dT%H%M%SZ)
OUT=$SF/$TAG; mkdir -m 700 "$OUT"
LOG=$OUT/score.log
s=$(date +%s)
CAP=$SF/captures
# 1. the copy of the root on .23 (the captures are laid over it in step 2, never into the live root)
D=$("${SSH23[@]}" bash -s -- "$TAG" 2> "$LOG" < <(cat <<'PREP'
set -eu
TAG=$1
V=/mnt/volume2/icsa-2027; ROOT=$V/calibration-11-rerun-f1c242a
W=$V/lane-snap-score; mkdir -p -m 700 $W; D=$W/$TAG
free=$(df --output=avail -BG $V | tail -1 | tr -dc 0-9); [ "$free" -ge 10 ] || { echo "refused: ${free}G free on .23" >&2; exit 2; }
mkdir -m 700 $D
nice -n 19 ionice -c3 rsync -a --exclude 'PAUSE*' --exclude RUN.pid --exclude WATCH.pid --exclude adapter_rows.jsonl --exclude h3_table.* --exclude rows.jsonl "$ROOT/" "$D/"
echo "$D"
PREP
)) || { echo "fidelity_score make: the copy on .23 failed: $(tail -n 2 "$LOG" | cut -c1-200)"; exit 2; }
# 2. the refreshed captures over the copy (when `captures` has run): the capture files and PULLS.jsonl (score reads those; pulls/ holds the raw reads, not needed by it, and stays the root's)
if [ -f "$CAP/PULLS.jsonl" ]; then
  nice -n 19 rsync -a -e "$RSH" "$CAP/audit.log" "$CAP/traefik.jsonl" "$CAP/PULLS.jsonl" "email-1@example:$D/" >> "$LOG" 2>&1 || { echo "fidelity_score make: the captures could not be laid over the copy"; exit 2; }
else
  echo "no refreshed captures ($CAP): the root's own captures are scored" >> "$LOG"
fi
# 3. the guard, then the score
"${SSH23[@]}" bash -s -- "$D" "${FIDELITY_ALLOW_STALE:-}" >> "$LOG" 2>&1 < <(cat <<'REMOTE'
set -eu
D=$1; ALLOW=$2
V=/mnt/volume2/icsa-2027; TREE=$V/wt/launch-f1c242a; PY=$TREE/.venv/bin/python
python3 -I - "$D" "$ALLOW" <<'PY'
import datetime as dt, glob, json, sys
d, allow = sys.argv[1], [x for x in sys.argv[2].split(",") if x]
ep = lambda s: dt.datetime.fromisoformat(s).timestamp()
iso = lambda t: dt.datetime.fromtimestamp(t, dt.timezone.utc).isoformat(timespec="seconds")
rows = [json.loads(x) for x in open(d + "/PULLS.jsonl") if x.strip()]
ends = []
for f in glob.glob(d + "/runs/*/run.json"):
    j = json.load(open(f))
    ends += [ep(j[k]) for k in ("run_end_utc", "lease_end_utc") if j.get(k)]
newest = max(ends)
res = {"newest_run_end": iso(newest), "allowed": allow, "captures": {}}
refuse = []
for n in ("audit.log", "traefik.jsonl"):
    t = max(ep(r["pulled_utc"]) for r in rows if r["name"] == n)
    late = int(newest - t) if t < newest else 0
    res["captures"][n] = {"pulled_utc": iso(t), "older_than_newest_run_s": late}
    if late and n not in allow:
        refuse.append(n)
    print(f"capture {n}: read the source {iso(t)}; newest run ended {iso(newest)}: " + (f"STALE by {late} s" if late else "covers it"))
json.dump(res, open(d + "/capture.age.json", "w"))
if refuse:
    print(f"REFUSED: {refuse} last read the source before the newest run ended: a run after it reads as uncovered (n_faulted 0). Refresh the capture, or name it in FIDELITY_ALLOW_STALE.")
    sys.exit(5)
PY
free=$(df --output=avail -BG $V | tail -1 | tr -dc 0-9); [ "$free" -ge 10 ] || { echo "refused: ${free}G free on .23"; exit 2; }
W=$V/lane-snap-score
cd $TREE
env -u ICSA_HOST_ALIASES -u ICSA_RESERVATION_DIR -u ICSA_RESERVED_KEYS -u ICSA_SLOT_KEYS -u ICSA_HARNESS_CONFIG_DIR -u ICSA_TOKEN_SOURCE PYTHONPATH=. PYTHONDONTWRITEBYTECODE=1 \
  nice -n 19 $V/bin/memcap ${SCORE_MEMCAP:-12} $PY -m icsa.faults.calibrate score --partial --out $D > $D/score.stdout 2> $D/score.stderr || { echo "score failed rc=$?"; tail -n 3 $D/score.stderr | cut -c1-200; exit 3; }
ls $D/adapter_rows.jsonl $D/h3_table.csv > /dev/null
echo "scored: $D rows=$(wc -l < $D/adapter_rows.jsonl)"
ls -1dt $W/*/ | tail -n +3 | xargs -r rm -rf          # keep the newest 2
REMOTE
)
rc=$?
if [ $rc -eq 0 ]; then
  for f in adapter_rows.jsonl h3_table.csv capture.age.json; do "${SSH23[@]}" "cat $D/$f" > "$OUT/$f.tmp" && mv "$OUT/$f.tmp" "$OUT/$f" || rc=4; done
fi
chmod 600 "$OUT"/* 2>/dev/null
[ $rc -ne 0 ] || echo "$TAG" > "$SF/LATEST.tmp" && [ $rc -ne 0 ] || mv -f "$SF/LATEST.tmp" "$SF/LATEST"
grep -E '^capture |^REFUSED' "$LOG" | cut -c1-260
echo "fidelity_score make rc=$rc seconds=$(( $(date +%s) - s )) files=$(ls "$OUT" | grep -c -E 'adapter_rows.jsonl|h3_table.csv')"
exit $rc
