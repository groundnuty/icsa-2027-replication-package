import numpy as np, xarray as xr, os, time, datetime as dt

base = "/data/icsa2027_data_20261101T090944Z/s1z"
os.makedirs("/tmp/mhw", exist_ok=True)

# Region cell indices (verified earlier): lat idx 48..107, lon idx 353..412
SL = (slice(48, 108), slice(353, 413))

def d(s): return dt.date(int(s[:4]), int(s[4:6]), int(s[6:]))
base_dates = [d("19911227") + dt.timedelta(days=i) for i in range((d("20030105")-d("19911227")).days+1)]
tgt_dates  = [d("20120601") + dt.timedelta(days=i) for i in range((d("20120831")-d("20120601")).days+1)]
print("base days:", len(base_dates), base_dates[0], base_dates[-1])
print("tgt days:", len(tgt_dates), tgt_dates[0], tgt_dates[-1])

def load(dates, tag):
    out = np.empty((len(dates), 60, 60), dtype=np.float64)
    t0 = time.time()
    for i, dd in enumerate(dates):
        p = f"{base}/sst_{dd.strftime('%Y%m%d')}.nc"
        ds = xr.open_dataset(p, engine="h5netcdf")
        out[i] = ds.analysed_sst[0, SL[0], SL[1]].values
        ds.close()
        if i % 400 == 0 or i == len(dates)-1:
            print(tag, i, "of", len(dates), "elapsed %.1fs" % (time.time()-t0), flush=True)
    return out

Vb = load(base_dates, "base")
Vt = load(tgt_dates, "tgt")
np.savez_compressed("/tmp/mhw/loaded.npz", Vb=Vb, Vt=Vt)
print("saved", Vb.dtype, Vt.dtype)
print("base finite frac:", np.isfinite(Vb).mean(), "tgt finite frac:", np.isfinite(Vt).mean())
