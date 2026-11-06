import numpy as np, datetime as dt
OUT = "/work/mhw"
z2 = np.load(f"{OUT}/results2.npz")
mcell = z2["mcell"]; active = z2["active"]
z1 = np.load(f"{OUT}/results1.npz")
tgt = np.load(f"{OUT}/tgt_0000_0092.npy")
tgt_dates = [dt.date(2004,6,1) + dt.timedelta(days=k) for k in range(92)]

print("cells in MHW per day (Jun 28 - Aug 21):")
for i in range(57, 81):
    print(tgt_dates[i].isoformat(), "active" if active[i] else "", int(mcell[i].sum()))

# look at a representative cell: find cell with max MHW span
spans = mcell.sum(axis=0)
cmax = int(np.argmax(spans))
print("\ncell index", cmax, "at lat-row,lon-col:", z1["sea_r"][cmax], z1["sea_c"][cmax], "span days:", spans[cmax])
mlen = [31,29,31,30,31,30,31,31,30,31,30,31]; mcum=[0]+list(np.cumsum(mlen))
doy_t = np.array([mcum[d.month-1]+d.day for d in tgt_dates])
T = tgt[:, z1["sea_r"], z1["sea_c"]]
thr_s = z1["thr_s"]
hot = T >= thr_s[doy_t-1]
for i in range(55, 83):
    print(tgt_dates[i].isoformat(), "TST=%.2f thr=%.2f hot=%d mhw=%d" % (T[i,cmax], thr_s[doy_t[i]-1, cmax], int(hot[i,cmax]), int(mcell[i,cmax])))
