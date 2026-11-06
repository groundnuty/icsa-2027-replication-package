
import xarray as xr,numpy as np
b=xr.open_dataarray("/tmp/b.nc");t=xr.open_dataarray("/tmp/t.nc")
s=b.sel(time=slice("1992-01-01","2002-12-31"))
jj=s.sel(time=s.time.dt.month.isin([7])).mean().item()
print(jj,t.sel(time=t.time.dt.month==7).mean().item())
print(t.mean(('latitude','longitude')).values[::6])
