"""Read-only on the data: run validate's scripted agent under the real tracer on a real pilot instance's S1 files through the
local Range server (no site_g, no sandbox), and stop before labelling, so the run directory can be labelled by label_one.py."""
import sys, json, time, resource
from pathlib import Path
from icsa.instruments import validate as V, confirm as C
class StopHere(Exception): pass
def stop(*a, **k): raise StopHere
option, layout, scen, inst, work = sys.argv[1:6]
data = C.real_world(inst)
k, sc = C.scenario(scen)
V.label_run = stop
t = time.time()
try:
    print("unexpected:", {x: v for x, v in V.run_case(option, layout, k, sc, data, Path(work)).items() if x in ("exit", "error")})
except StopHere:
    print("agent finished, stopped before label_run")
print(option, layout, scen, "wall_s", round(time.time() - t, 1), "self_maxrss_gib", round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 2**20, 2),
      "children_maxrss_gib", round(resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss / 2**20, 2))
