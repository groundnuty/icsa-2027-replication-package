import numpy as np, datetime

full_mask = np.load("/tmp/mhw/full_mask.npy")
ndays = full_mask.shape[0]
d0 = datetime.date(2007, 6, 1)
active = full_mask.any(axis=(1, 2))
profile = "".join("#" if a else "." for a in active)
print("active profile 2007-06-01..2007-08-31:")
for i in range(0, ndays, 31):
    print(d0 + datetime.timedelta(days=i), profile[i:i+31])
events = np.load("/tmp/mhw/events.npy", allow_pickle=True)
print("events:", events)

# per-cell stats
sea = np.load("/tmp/mhw/sea_cells.npy")
n_cells_in_mhw = int(full_mask.any(axis=0).sum())
print("sea cells that ever entered an MHW:", n_cells_in_mhw)
