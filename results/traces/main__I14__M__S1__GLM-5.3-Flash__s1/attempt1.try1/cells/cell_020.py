import numpy as np, datetime as dt

z = np.load("/work/cache_sst.npz"); tgt32 = z["tgt"]; tgt_ord = z["tgt_ord"]
z2 = np.load("/work/cache_thr2.npz"); thr = z2["thr"]
zm = np.load("/work/cache_mhw.npz"); mhw = zm["mhw"]
tgt64 = tgt32.astype(np.float64)
tgt_doy = np.array([dt.date.fromordinal(int(o)).timetuple().tm_yday for o in tgt_ord], dtype=np.int32)
sea = np.all(np.isfinite(tgt64), axis=0)
hot = (tgt64 >= thr[tgt_doy-1]) & sea[None, :, :]
dates = [dt.date.fromordinal(int(o)) for o in tgt_ord]
print("index 30 = %s, index 37 = %s" % (dates[30], dates[37]))

for k, label in [(30, "Jul 1"), (37, "Jul 8")]:
    cells = np.argwhere(mhw[k])
    print(f"{label} ({dates[k]}): {len(cells)} cells in MHW")
    for i, j in cells:
        sst_series = np.round(tgt64[:, i, j], 2)
        print(f"  cell ({i},{j}) lat {53.5+0.02*(132+i):.2f} lon {9.0+0.02*(436+j):.2f}")
        print("   hot Jun-Aug:", "".join(map(str, hot[:,i,j].astype(int))), "| mhw:", "".join(map(str, mhw[:,i,j].astype(int))))
        print("   SST Jun20-Jul14:", sst_series[19:44])
        print("   thr Jun20-Jul14:", np.round(thr[tgt_doy[19:44]-1, i, j], 2))
