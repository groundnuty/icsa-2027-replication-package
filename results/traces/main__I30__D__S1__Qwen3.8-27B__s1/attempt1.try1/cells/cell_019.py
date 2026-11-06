import numpy as np
z = np.load('/work/sst_region.npz', allow_pickle=False)
A = z['A']; dates = [str(d) for d in z['dates']]
mz = np.load('/work/mhw_intermediate.npz', allow_pickle=False)
mask, sea, tgt_dates = mz['mask'], mz['sea'], [str(d) for d in mz['tgt_dates']]
hot = None
# recompute hot quickly for inspection
tc = np.load('/work/thr_cli.npz', allow_pickle=False)
thr_s = tc['thr_s']
d2i = {d: i for i, d in enumerate(dates)}
mdays = [31,29,31,30,31,30,31,31,30,31,30,31]
cum=[0]
for m in mdays: cum.append(cum[-1]+m)
def doy(s): return cum[int(s[5:7])-1] + int(s[8:10])
tdoy = np.array([doy(s) for s in tgt_dates])
tgt = A[d2i['2010-06-01']:d2i['2010-08-31']+1]
sea_cells = np.argwhere(sea)
hot = np.array([(tgt[t] >= thr_s[tdoy[t]])[sea] for t in range(len(tgt))])

print("per-day hot counts and active (t, date, nhot, active):")
for t in range(len(tgt_dates)):
    print(t, tgt_dates[t], int(hot[t].sum()), bool(mask[t].any()), flush=True)
