
import json
import numpy as np, xarray as xr

# independent MHW recompute (fresh) for comparison with written mask
sea2 = np.load("/tmp/sea2.npy"); thrS = np.load("/tmp/thrS.npy")
X_tgt = np.load("/tmp/X_tgt.npy")
ds0 = xr.open_dataset("/data/icsa2027_data_20261101T090944Z/s2z/sst_s2.nc", engine="h5netcdf")
t = ds0.time.values
t_tgt = t[10378:10470]
si = np.argwhere(sea2)
mlen=[31,29,31,30,31,30,31,31,30,31,30,31]
mdoy = np.zeros((12,31), int); off=0
for m in range(12):
    mdoy[m,:mlen[m]] = off+1+np.arange(mlen[m]); off+=mlen[m]
def md_of(dt):
    mo = int(np.datetime64(dt,'M').astype(np.int64))%12
    day = int(np.datetime64(dt,'D').astype(np.int64)-np.datetime64(np.datetime64(dt,'M'),'D').astype(np.int64))+1
    return mo,day
doy_t = np.array([mdoy[md_of(dt)[0], md_of(dt)[1]-1] for dt in t_tgt])
hot = X_tgt >= thrS[:, doy_t-1].T
def cell_mhw(h):
    out = np.zeros_like(h, bool)
    d = np.diff(np.concatenate(([0], h, [0])))
    s = np.flatnonzero(d==1); e = np.flatnonzero(d==-1)-1
    keep=(e-s+1)>=5; cur=None; ivs=[]
    for a,b in zip(s[keep], e[keep]):
        if cur is not None and a-cur[1]-1<=2: cur=(cur[0],b)
        else:
            if cur: ivs.append(cur)
            cur=(a,b)
    if cur: ivs.append(cur)
    for a,b in ivs: out[a:b+1]=True
    return out
ref = np.stack([cell_mhw(hot[:,c]) for c in range(len(si))], axis=1)

out = xr.open_dataset("output/mhw_mask.nc", engine="h5netcdf")
print(out)
m = out.mhw
print("dtype:", m.dtype, "dims:", m.dims)
lat, lon, tm = out.lat.values, out.lon.values, out.time.values
print("lat range:", lat.min(), lat.max(), "lon range:", lon.min(), lon.max(), "n:", len(lat), len(lon), len(tm))
print("time:", tm[0], "...", tm[-1])
latm = (ds0.latitude.values>=56.63)&(ds0.latitude.values<=57.83)
lonm = (ds0.longitude.values>=20.23)&(ds0.longitude.values<=21.43)
assert np.array_equal(lat, ds0.latitude.values[latm])
assert np.array_equal(lon, ds0.longitude.values[lonm])
assert np.array_equal(tm, t_tgt)
mv = m.values
print("unique values:", np.unique(mv))
# sea cells must match ref; non-sea must be 0
msea = mv[:, si[:,0], si[:,1]]
print("sea mismatch:", int((msea.astype(bool) != ref).sum()))
landmask = ~sea2
print("land non-zero:", int(mv[:, landmask].sum()))
# region bounds inclusive check
print("region exact:", float(lat.min()), float(lat.max()), float(lon.min()), float(lon.max()))

print(json.dumps(json.load(open("output/report.json")), indent=2))
osize = __import__("os").path.getsize("output/mhw_mask.nc")
print("mhw_mask.nc bytes:", osize)
