import numpy as np, pickle

with open("/tmp/sst_data.pkl","rb") as f: D = pickle.load(f)
with open("/tmp/thr.pkl","rb") as f: T = pickle.load(f)
with open("/tmp/mhw_state.pkl","rb") as f: S = pickle.load(f)

sea = D["sea"]
flat = np.flatnonzero(sea)
print("T cell_idx: len", len(T["cell_idx"]), "first5", T["cell_idx"][:5], "last5", T["cell_idx"][-5:])
print("T == flat:", bool((T["cell_idx"] == flat).all()))
print("S cell_idx: len", len(S["cell_idx"]), "first5", S["cell_idx"][:5], "last5", S["cell_idx"][-5:])
print("S == T:", S["cell_idx"].shape == T["cell_idx"].shape and bool((S["cell_idx"] == T["cell_idx"]).all()))
print("S == T//60:", bool((S["cell_idx"] == T["cell_idx"]//60).all()))
# check mask alignment: recompute hot for columns vs S hot
CUM = np.array([0, 31, 60, 91, 121, 152, 182, 213, 244, 274, 305, 335])
doy_t = np.array([CUM[dt.month-1] + dt.day for dt in D["time_target"]])
sst_c = D["sst_target"].reshape(92, 3600)[:, flat]
hot_now = sst_c >= T["thr_s"][doy_t, :]
print("hot recomputed vs S hot (same ordering):", bool((hot_now == S["hot"]).all()))
