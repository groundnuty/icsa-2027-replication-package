import fsspec, xarray as xr, numpy as np, pandas as pd, time as timer, warnings

t0 = timer.time()
fs = fsspec.filesystem('onedata')
f = fs.open('icsa2027_data_20261101T090944Z/s2z/sst_s2.nc', 'rb')
ds = xr.open_dataset(f, engine='h5netcdf')
lat = ds.latitude.values; lon = ds.longitude.values
latidx = np.where((lat >= 56.13) & (lat <= 57.33))[0]
lonidx = np.where((lon >= 17.71) & (lon <= 18.91))[0]
times = pd.DatetimeIndex(ds.time.values)

# Baseline window incl. the +/-5-day shoulders allowed by the method
b0, b1 = pd.Timestamp('1991-12-27'), pd.Timestamp('2003-01-05')
bidx = np.where((times >= b0) & (times <= b1))[0]
bdates = times[bidx]
arr = ds.analysed_sst.isel(time=bidx, latitude=latidx, longitude=lonidx).values.astype(np.float64)
print("baseline window loaded:", bdates[0].date(), "->", bdates[-1].date(), arr.shape, round(timer.time()-t0,1), "s", flush=True)

# Target period
tidx = np.where((times >= pd.Timestamp('2015-06-01')) & (times <= pd.Timestamp('2015-08-31')))[0]
tdates = times[tidx]
sst = ds.analysed_sst.isel(time=tidx, latitude=latidx, longitude=lonidx).values.astype(np.float64)
print("target loaded:", tdates[0].date(), "->", tdates[-1].date(), sst.shape, round(timer.time()-t0,1), "s", flush=True)
ds.close(); f.close()

sea = np.isfinite(sst).all(axis=0)
fin_any = np.isfinite(sst).any(axis=0)
print("sea cells (finite all 92 target days):", int(sea.sum()), "/", sea.size,
      "| partially-finite:", int((fin_any & ~sea).sum()), "| never finite:", int((~fin_any).sum()))
print("baseline finite fraction:", round(float(np.isfinite(arr).mean()), 4))

# quantile method sanity checks (expect 9.5 and 2.4)
print("hazen check1:", np.quantile(np.arange(1,11,dtype=float), 0.9, method='hazen'))
print("hazen check2:", np.nanquantile(np.array([1.,2.,np.nan,4.]), 0.9, method='hazen'))

# remapped day-of-year (1..366; Feb29=60; Mar1=61 always)
m_start = np.array([1,32,61,92,122,153,183,214,245,275,306,336])
bdoy = m_start[bdates.month.values-1] + bdates.day.values - 1
tdoy = m_start[tdates.month.values-1] + tdates.day.values - 1
print("target doy range:", tdoy[0], "->", tdoy[-1])
print("baseline doys present: min", bdoy.min(), "max", bdoy.max(), "count of 60:", int((bdoy==60).sum()))

pos0 = bdates[0]
years = range(1992, 2003)

def md_of_doy(d):
    mi = int(np.searchsorted(m_start, d, side='right') - 1)
    return mi + 1, int(d - m_start[mi] + 1)
for dd in [1, 59, 60, 61, 153, 244, 365, 366]:
    print("doy", dd, "-> (month,day)", md_of_doy(dd))
