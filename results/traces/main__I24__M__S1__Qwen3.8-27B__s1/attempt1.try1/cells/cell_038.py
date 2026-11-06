import numpy as np, datetime as dt
import xarray as xr
chk = xr.open_dataset("output/mhw_mask.nc", engine="h5netcdf")
m = chk["mhw"].values
print("dtype:", m.dtype, "shape:", m.shape)
active = m.any(axis=(1,2))
print("active dtype:", active.dtype, "n active days:", int(active.sum()))
padded = np.concatenate(([0], active.astype(np.int8), [0]))
d = np.diff(padded)
idx = np.flatnonzero(d == 1)
ends = np.flatnonzero(d == -1) - 1
print("onset idx:", idx, "end idx:", ends)
tgt_dates = [dt.date(2004,6,1) + dt.timedelta(days=k) for k in range(92)]
for s,e in zip(idx, ends):
    print("event from saved mask:", tgt_dates[s], "->", tgt_dates[e])
# also raw file inspection
import h5py
with h5py.File("output/mhw_mask.nc", "r") as f:
    print("vars:", list(f.keys()))
    mv = f["mhw"]
    print("mhw shape/dtype:", mv.shape, mv.dtype)
    print("time raw:", f["time"][0], f["time"][-1], dict(mv.attrs))
