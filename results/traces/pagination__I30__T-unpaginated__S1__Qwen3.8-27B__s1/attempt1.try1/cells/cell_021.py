
import sys, numpy as np, datetime as dt
sys.path.insert(0,'/work/mhw')
import common

ext, tgt, done = common.load_state()
print('ext', ext.shape, ext.dtype, 'tgt', tgt.shape, tgt.dtype)
print('all fetched (no all-NaN rows):', not np.any(np.all(np.isnan(ext),axis=1)) and not np.any(np.all(np.isnan(tgt),axis=1)))

# NaNs per row (across cells) in the extended window and target
nan_ext = np.isnan(ext).sum(axis=1)
nan_tgt = np.isnan(tgt).sum(axis=1)
print('ext: rows with any NaN:', (nan_ext>0).sum(), 'max NaNs in a row:', nan_ext.max())
print('tgt: rows with any NaN:', (nan_tgt>0).sum(), 'max NaNs in a row:', nan_tgt.max())

# sea cells: finite on every target day
sea = np.all(np.isfinite(tgt), axis=0)
print('sea cells:', sea.sum(), 'of', sea.size)
# how many of those have any NaN in baseline window?
sea_bad = [~np.all(np.isfinite(ext[:,i]),axis=0) for i in range(0) ]
nbad = sum(int(np.isnan(ext[:,i]).any()) for i in np.flatnonzero(sea))
print('sea cells with >=1 NaN in baseline window:', nbad)

# date -> index map & day-of-year (leap mapping)
ext_dates, tgt_dates = common.all_dates()
pos = {common.datekey(d): i for i, d in enumerate(ext_dates)}
def doy_leap(d):
    return dt.date(2000, d.month, d.day).timetuple().tm_yday
doy_ext = np.array([doy_leap(d) for d in ext_dates])
doy_tgt = np.array([doy_leap(d) for d in tgt_dates])
print('target doys:', doy_tgt.min(), doy_tgt.max())
np.save('/work/mhw/doy_ext.npy', doy_ext); np.save('/work/mhw/doy_tgt.npy', doy_tgt)
np.save('/work/mhw/sea.npy', sea)
print('saved helpers')
