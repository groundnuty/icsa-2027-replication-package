import numpy as np, warnings

z = np.load("work/sst.npz", allow_pickle=False)
base64 = z["base_arr"].astype(np.float64)
tgt64 = z["tgt_arr"].astype(np.float64)
lat = z["lat"]; lon = z["lon"]
win_idx = np.load("work/win_idx.npy", allow_pickle=True).item()

finite_all = np.all(np.isfinite(tgt64), axis=0)
sea_idx = np.where(finite_all.ravel())[0]
n_sea = len(sea_idx)
print("n_sea:", n_sea)

# NaN share of baseline at sea cells
base_sea = base64[:, sea_idx]
print("baseline NaN fraction at sea cells:", np.isnan(base_sea).mean().round(6))
# any pool with an all-NaN column? (a sea cell with zero baseline values for some d)
allnan_d = []
for d in range(1, 367):
    if d == 60: continue
    P = base64[win_idx[d]][:, sea_idx]
    if np.all(np.isnan(P), axis=0).any():
        allnan_d.append(d)
print("days with an all-NaN pool column:", allnan_d[:10], len(allnan_d))

thr = np.full((n_sea, 366), np.nan)
cli = np.full((n_sea, 366), np.nan)
with warnings.catch_warnings():
    warnings.simplefilter("ignore")
    for d in range(1, 367):
        if d == 60: continue
        P = base64[win_idx[d]][:, sea_idx]          # (121, n_sea)
        thr[:, d] = np.quantile(P, 0.9, method="hazen", axis=0, nan_policy="omit")
        cli[:, d] = np.nanmean(P, axis=0)

# day 60 = mean of 59 and 61 (before smoothing)
thr[:, 60] = 0.5 * (thr[:, 59] + thr[:, 61])
cli[:, 60] = 0.5 * (cli[:, 59] + cli[:, 61])
print("any NaN left in thr/cli:", np.isnan(thr).any(), np.isnan(cli).any())

# 31-day centred circular moving mean over the 366-element array
darr = np.arange(366)
idx = (darr[None, :] - 15 + np.arange(31)) % 366     # (31, 366)
G = np.take(idx, darr[:, None], axis=1)              # G[d, k] = (d-15+k) mod 366
thr_s = np.take(thr, G, axis=1).mean(axis=2)
cli_s = np.take(cli, G, axis=1).mean(axis=2)
print("smoothing check: max |thr_s - thr|:", np.abs(thr_s - thr).max().round(4))
print("thr_s range (sea cells):", thr_s.min().round(4), thr_s.max().round(4), " (K)")
print("cli_s range:", cli_s.min().round(4), cli_s.max().round(4))
print("thr for midsummer (doy 200) sample:", thr_s[0, 195:205].round(3))

np.savez_compressed("work/stats.npz", thr=thr, cli=cli, thr_s=thr_s, cli_s=cli_s,
                    sea_idx=sea_idx, lat=lat, lon=lon)
print("saved work/stats.npz")
