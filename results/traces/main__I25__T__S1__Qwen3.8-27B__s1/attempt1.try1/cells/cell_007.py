
import fsspec, xarray as xr, numpy as np, time
fs = fsspec.filesystem('onedata')
t0=time.time()
f = fs.open('/icsa2027_data_20261101T090944Z/s1z/sst_20160601.nc','rb')
raw = f.read()
f.close()
print("download 1 file: %.2f s, %d bytes" % (time.time()-t0, len(raw)))
import netCDF4
import io
ds = xr.open_dataset(io.BytesIO(raw), engine='h5netcdf')
v = ds.analysed_sst
print("units:", v.attrs.get('units'), "long_name:", v.attrs.get('long_name'))
print("dtype:", v.dtype)
print("time:", ds.time.values)
lat = ds.latitude.values; lon = ds.longitude.values
print("lat range", lat.min(), lat.max(), "lon range", lon.min(), lon.max())
sel = v.values[0]
print("sample values in region:")
# find region indices
ilat = np.where((lat>=57.57-1e-9)&(lat<=58.77+1e-9))[0]
ilon = np.where((lon>=10.25-1e-9)&(lon<=11.45+1e-9))[0]
print("n lat cells:", len(ilat), ilat[0], ilat[-1], lat[ilat[0]], lat[ilat[-1]])
print("n lon cells:", len(ilon), ilon[0], ilon[-1], lon[ilon[0]], lon[ilon[-1]])
sub = sel[ilat[0]:ilat[-1]+1, ilon[0]:ilon[-1]+1]
print("sub shape", sub.shape, "finite:", np.isfinite(sub).sum(), "min/max:", np.nanmin(sub), np.nanmax(sub))
print("global min/max:", np.nanmin(sel), np.nanmax(sel))
ds.close()
