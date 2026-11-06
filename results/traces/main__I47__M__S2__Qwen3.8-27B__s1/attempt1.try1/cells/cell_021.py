import numpy as np, json

m = np.load("work/mhw.npz")
mhw = m["mhw"]; tgt_dates = m["tgt_dates"].astype("datetime64[D]"); active = m["active"]
str_dates = [str(d) for d in tgt_dates]

act_idx = [str_dates[i] for i in range(len(str_dates)) if active[i]]
print("active days (%d):" % len(act_idx))
print(act_idx)

ev = json.load(open("work/events.json"))
for s, e in ev:
    i0, i1 = str_dates.index(s), str_dates.index(e)
    sub = mhw[i0:i1+1]
    per = sub.sum(axis=1)
    print(f"event {s}..{e}: {i1-i0+1} days")
    print("  cells in MHW per day:", per.tolist())
    print("  min/mean/max:", per.min(), round(float(per.mean()),1), per.max())
    # gap check around event boundaries
    if i0 > 0:
        print("  day before onset cells:", mhw[i0-1].sum())
    if i1 < len(str_dates)-1:
        print("  day after end cells:", mhw[i1+1].sum())
