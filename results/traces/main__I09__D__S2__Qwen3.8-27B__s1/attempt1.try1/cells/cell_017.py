import numpy as np
z = np.load('/work/intermediate.npz')
M = z['M']; t_tgt = z['t_tgt']  # (92, 3600) uint8, dates
doy_tgt = z['doy_tgt']

# per-day active cell counts
active_counts = M.sum(axis=1)
print("active cell counts per day (first 20 days of period):")
for i in range(0, 92, 4):
    print(" ", t_tgt[i].astype('datetime64[D]'), int(active_counts[i]))

# independent event extraction: find zero-active-day breaks
active = (active_counts > 0)
starts = np.flatnonzero(np.concatenate(([active[0]], active[1:] & ~active[:-1])))
ends   = np.flatnonzero(np.concatenate((active & ~np.roll(active, -1), [False])) )
# simpler: scan
events = []
i = 0
while i < 92:
    if active[i]:
        j = i
        while j + 1 < 92 and active[j+1]:
            j += 1
        events.append((str(t_tgt[i].astype('datetime64[D]')), str(t_tgt[j].astype('datetime64[D]')), j - i + 1))
        i = j + 1
    else:
        i += 1
print("\nindependent events (onset, end, length):")
for ev in events:
    print("  ", ev)

# verify M only on sea cells, and that no MHW run crosses period boundary improperly
# check: for each cell, every 1-run in M is >=5 long and its 'core' hot structure consistent
# also check mask dtype/shape
print("\nM shape:", M.shape, M.dtype, "min/max:", M.min(), M.max())

# distribution of per-cell MHW coverage
sea = (np.isfinite(z['thr'][:, :]).any(axis=0))
per_cell_days = M.sum(axis=0)
print("cells with any MHW day:", int((per_cell_days > 0).sum()), "of", int(sea.sum()))
print("max MHW days in a cell:", int(per_cell_days.max()), "mean over cells w/ MHW:", round(float(per_cell_days[per_cell_days>0].mean()), 1))
