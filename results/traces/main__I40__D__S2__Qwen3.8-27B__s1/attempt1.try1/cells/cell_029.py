import h5py, numpy as np, datetime, time
f = h5py.File('/work/sst_s2.nc', 'r')
v = f['analysed_sst']
E0 = datetime.date(1982,1,1)
def i_of(d): return (d - E0).days

la = np.asarray(f['latitude'])[404:464].copy()
lo = np.asarray(f['longitude'])[559:619].copy()
np.save('/work/region_lat.npy', la)
np.save('/work/region_lon.npy', lo)
print("lat:", la[0], la[-1], "lon:", lo[0], lo[-1])

# extended baseline: 1991-12-27 .. 2003-01-05
b0 = i_of(datetime.date(1991,12,27)); b1 = i_of(datetime.date(2003,1,5))
print("baseline ext idx:", b0, b1, "n days:", b1-b0+1)
t0=time.time()
V_base = v[b0:b1+1, 404:464, 559:619]
V_base = np.ascontiguousarray(V_base, dtype=np.float32)
print("V_base read:", V_base.shape, V_base.dtype, time.time()-t0)

# target: 2009-06-01 .. 2009-08-31
g0 = i_of(datetime.date(2009,6,1)); g1 = i_of(datetime.date(2009,8,31))
print("target idx:", g0, g1, "n days:", g1-g0+1)
t0=time.time()
V_tgt = v[g0:g1+1, 404:464, 559:619]
V_tgt = np.ascontiguousarray(V_tgt, dtype=np.float32)
print("V_tgt read:", V_tgt.shape, V_tgt.dtype, time.time()-t0)

np.save('/work/V_base.npy', V_base)
np.save('/work/V_tgt.npy', V_tgt)

# quick sanity
for name, V in [("baseline", V_base), ("target", V_tgt)]:
    fin = np.isfinite(V)
    print(name, "finite fraction:", fin.mean())
    # per-day finite counts
    fc = fin.sum(axis=(1,2))
    print(name, "per-day finite min/max:", fc.min(), fc.max(), "days with all finite:", (fc==V.shape[1]*V.shape[2]).sum())
f.close()
