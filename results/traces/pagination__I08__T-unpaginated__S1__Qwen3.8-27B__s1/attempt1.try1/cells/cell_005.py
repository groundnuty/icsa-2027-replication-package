
import fsspec, xarray as xr, numpy as np, time
fs = fsspec.filesystem('onedata')
base = '/icsa2027_data_20261101T090944Z/s1z'

with fs.open(base + '/sst_20070601.nc', "rb") as f:
    ds = xr.open_dataset(f, engine="h5netcdf")
    lat = ds['latitude'].values.astype(np.float64)
    lon = ds['longitude'].values.astype(np.float64)
    # region mask
    mlat = (lat >= 54.81 - 1e-6) & (lat <= 56.01 + 1e-6)
    mlon = (lon >= 19.61 - 1e-6) & (lon <= 20.81 + 1e-6)
    ilat = np.where(mlat)[0]
    ilon = np.where(mlon)[0]
    print("n lat:", len(ilat), "n lon:", len(ilon))
    print("lat range:", lat[ilat[0]], lat[ilat[-1]])
    print("lon range:", lon[ilon[0]], lon[ilon[-1]])
    print("lat idx:", ilat[0], ilat[-1], "lon idx:", ilon[0], ilon[-1])
    # check spacing regularity
    print("dlat:", np.diff(lat[ilat])[:3], "dlon:", np.diff(lon[ilon])[:3])
    # check grid regularity: is lat exactly 53.5 + 0.02*k in float64?
    k = (lat - 53.5) / 0.02
    print("k max err:", np.abs(k - np.round(k)).max())
    k2 = (lon - 9.0) / 0.02
    print("k2 max err:", np.abs(k2 - np.round(k2)).max())
    # test sliced read speed
    t0 = time.time()
    sub = ds['analysed_sst'].isel(time=slice(0,1), latitude=slice(ilat[0], ilat[-1]+1), longitude=slice(ilon[0], ilon[-1]+1)).values
    t1 = time.time()
    print("sliced read shape:", sub.shape, "type:", sub.dtype, "time:", round(t1-t0, 3), "s")
    print("finite fraction:", np.isfinite(sub).mean())
    print("sample:", sub[0, ipv6-4, ipv6-4])
    print("var encoding:", ds['analysed_sst'].encoding)
    ds.close()
