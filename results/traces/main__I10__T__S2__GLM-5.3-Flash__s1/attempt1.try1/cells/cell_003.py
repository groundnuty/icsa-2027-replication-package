import fsspec, xarray as xr, numpy as np, pandas as pd

fs = fsspec.filesystem('onedata')
path = "icsa2027_data_20261101T090944Z/s2z/sst_s2.nc"
f = fs.open(path, "rb")
ds = xr.open_dataset(f, engine="h5netcdf")
print("sst attrs:", ds.analysed_sst.attrs)
print("encoding:", {k:v for k,v in ds.analysed_sst.encoding.items() if k in ('dtype','_FillValue','scale_factor','add_offset','units','calendar')})

t = pd.to_datetime(ds.time.values)
t0 = pd.Timestamp("1982-01-01")
print("offset check:", (t - t0).days[:3], (t - t0).days[-3:])

i_base0 = (pd.Timestamp("1991-12-27") - t0).days
i_base1 = (pd.Timestamp("2003-01-05") - t0).days
i_tgt0  = (pd.Timestamp("2005-06-01") - t0).days
i_tgt1  = (pd.Timestamp("2005-08-31") - t0).days
print("time idx:", i_base0, i_base1, i_tgt0, i_tgt1, "nbase_ext:", i_base1-i_base0+1, "ntgt:", i_tgt1-i_tgt0+1)
print("t at idx:", t[i_base0], t[i_base1], t[i_tgt0], t[i_tgt1])
