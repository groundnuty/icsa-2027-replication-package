import numpy as np
active = np.load("/tmp/active.npy")
tt = np.load("/tmp/tgt_times.npy")
EPOCH = np.datetime64("1970-01-01")
tdates = (EPOCH + tt.astype("timedelta64[D]")).astype(str)
print("target day0:", tdates[0], " last:", tdates[-1])
idx = np.where(active)[0]
print("first active idx:", idx[0], tdates[idx[0]], " last active idx:", idx[-1], tdates[idx[-1]])
print("contiguous:", np.array_equal(idx, np.arange(idx[0], idx[-1]+1)))

# event extraction (maximal runs of active days)
runs = []
t = 0; T = len(active)
while t < T:
    if active[t]:
        u = t
        while u+1 < T and active[u+1]:
            u += 1
        runs.append((t, u)); t = u+1
    else:
        t += 1
events = [{"onset": str(tdates[s]), "end": str(tdates[e])} for s, e in runs]
import json
print(json.dumps(events, indent=1))
print("n events:", len(events))
np.save("/tmp/events_idx.npy", np.array(runs))
