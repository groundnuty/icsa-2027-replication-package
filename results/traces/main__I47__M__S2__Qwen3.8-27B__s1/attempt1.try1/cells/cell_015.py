import numpy as np

z = np.load("work/sst.npz", allow_pickle=False)
base64 = z["base_arr"].astype(np.float64).reshape(z["base_arr"].shape[0], -1)
tgt64 = z["tgt_arr"].astype(np.float64).reshape(z["tgt_arr"].shape[0], -1)
lat = z["lat"]; lon = z["lon"]
win_idx = np.load("work/win_idx.npy", allow_pickle=True).item()

finite_all = np.all(np.isfinite(tgt64), axis=0)
sea_idx = np.where(finite_all.ravel())[0]
n_sea = len(sea_idx)
print("n_sea:", n_sea)

thr = np.full((n_sea, 366), np.nan)
cli = np.full((n_sea, 366), np.nan)
for d in range(1, 367):
    if d == 60: continue
    P = base64[win_idx[d]][:, sea_idx]
    assert not np.isnan(P).any(), f"NaN in pool for d={d}"
    thr[:, d-1] = np.quantile(P, 0.9, method="hazen", axis=0)
    cli[:, d-1] = np.nanmean(P, axis=0)

thr[:, 59] = 0.5 * (thr[:, 58] + thr[:, 60])
cli[:, 59] = 0.5 * (cli[:, 58] + cli[:, 60])
print("any NaN left in thr/cli:", np.isnan(thr).any(), np.isnan(cli).any())

darr = np.arange(366)
G = (darr[:, None] - 15 + np.arange(31)[None, :]) % 366    # (366, 31): G[d,k]=(d-15+k) mod 366
assert list(G[0]) == list(range(351, 366)) + list(range(0, 16)), G[0]
assert list(G[100]) == list(range(85, 116))
thr_s = np.take(thr, G, axis=1).mean(axis=2)   # (n_sea, 366)
cli_s = np.take(cli, G, axis=1).mean(axis=2)
print("smoothing sanity: max |thr_s - thr|:", np.abs(thr_s - thr).max().round(4))
print("thr_s range (K):", thr_s.min().round(4), thr_s.max().round(4),
      " (C:", (thr_s.min()-273.15).round(2), "..", (thr_s.max()-273.15).round(2), ")")
print("cli_s range (K):", cli_s.min().round(4), cli_s.max().round(4),
      " (C:", (cli_s.min()-273.15).round(2), "..", (cli_s.max()-273.15).round(2), ")")
print("thr_s cell0 doy196..204:", thr_s[0, 195:205].round(3))

np.savez_compressed("work/stats.npz", thr=thr, cli=cli, thr_s=thr_s, cli_s=cli_s,
                    sea_idx=sea_idx, lat=lat, lon=lon)
print("saved work/stats.npz")
