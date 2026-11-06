import numpy as np, xarray as xr, pandas as pd, os, time as _t
os.makedirs('/work/output', exist_ok=True)

path='/work/sst_s2.nc'
ds = xr.open_dataset(path, engine='h5netcdf')
lat = ds.latitude.values          # float32
lon = ds.longitude.values         # float32
t   = ds.time.values              # datetime64[ns]

m_lat = (lat>=54.17)&(lat<=55.37)
m_lon = (lon>=13.25)&(lon<=14.45)
li = np.flatnonzero(m_lat); oi = np.flatnonzero(m_lon)
print("n lat:", li.size, "n lon:", oi.size)

def idx(datestr):
    return int(np.searchsorted(t, np.datetime64(datestr,'D')))

# ---- target period ----
i0, i1 = idx('2014-06-01'), idx('2014-08-31')+1
assert t[i0]==np.datetime64('2014-06-01','D') and t[i1-1]==np.datetime64('2014-08-31','D')
nt = i1-i0
sst_t = ds.analysed_sst.isel(time=slice(i0,i1), latitude=li, longitude=oi).values.astype(np.float64)
print("target shape:", sst_t.shape)
sea = np.all(np.isfinite(sst_t), axis=0)
n_sea = int(sea.sum())
print("sea cells (finite all target days):", n_sea)

# ---- baseline window ----
j0, j1 = idx('1991-12-27'), idx('2003-01-05')+1
assert t[j0]==np.datetime64('1991-12-27','D') and t[j1-1]==np.datetime64('2003-01-05','D')
sst_b = ds.analysed_sst.isel(time=slice(j0,j1), latitude=li, longitude=oi).values.astype(np.float64)
print("baseline window shape:", sst_b.shape)

np.savez_compressed('/work/interim.npz', sst_t=sst_t, sst_b=sst_b, li=li, oi=oi, sea=sea,
                    lat=lat[li], lon=lon[oi], t_i0=i0, t_i1=i1)
print("saved interim")
