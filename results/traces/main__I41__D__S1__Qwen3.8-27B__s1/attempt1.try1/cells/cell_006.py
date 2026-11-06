import xarray as xr, numpy as np
ds = xr.open_dataset('/work/data/sst_20210601.nc', engine='h5netcdf')
sst = ds['analysed_sst']
print("units:", sst.attrs.get('units'), "long_name:", sst.attrs.get('long_name'))
print(sst.encoding)
lat = ds['latitude'].values
lon = ds['longitude'].values
print("lat range", lat.min(), lat.max(), "lon range", lon.min(), lon.max())
latm = (lat >= 61.57) & (lat <= 62.77)
lonm = (lon >= 20.17) & (lon <= 21.37)
print("n lat cells:", latm.sum(), "n lon cells:", lonm.sum())
print("lat bounds in region:", lat[latm].min(), lat[latm].max())
print("lon bounds in region:", lon[lonm].min(), lon[lonm].max())
sub = sst.values[0][latm][:, lonm]
print("region SST shape:", sub.shape)
print("finite:", np.isfinite(sub).sum(), "of", sub.size)
print("min/max finite:", np.nanmin(sub), np.nanmax(sub))
print("any NaN:", np.isnan(sub).any())
# print a few values to see if Kelvin
print("sample values:", sub[np.isfinite(sub)][:5])
