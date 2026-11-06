import numpy as np, xarray as xr, time, json
import datetime as dtm

t_start = time.time()
ds = xr.open_dataset('/work/s2z/sst_s2.nc', engine='h5netcdf')
t = ds.time.values
lat = ds.latitude.values; lon = ds.longitude.values
lat_idx = np.where((lat >= 56.09) & (lat <= 57.29))[0]
lon_idx = np.where((lon >= 10.55) & (lon <= 11.75))[0]
idx = np.load('/work/idx.npz'); j0, j1 = int(idx['j0']), int(idx['j1'])
tgt_dates = t[j0:j1].astype('datetime64[D]')
print('target days:', len(tgt_dates), str(tgt_dates[0]), '..', str(tgt_dates[-1]))

z = np.load('/work/thr_clim.npz')
thr_s = z['thr_s']; clim_s = z['clim_s']   # (366,60,60) float64

cum = np.array([0,31,60,91,121,152,182,213,244,274,305,335])
def doy_of(dates):
    months = dates.astype('datetime64[M]')
    m = (months - months.astype('datetime64[Y]')).astype(int)
    return cum[m] + ((dates - months).astype(int) + 1)
doy_t = doy_of(tgt_dates) - 1   # 0-based index into 366 arrays
print('target doys (1-based):', doy_t[0]+1, '..', doy_t[-1]+1)

sst = ds.analysed_sst.isel(time=slice(j0, j1), latitude=lat_idx, longitude=lon_idx).values.astype(np.float64)
print('sst', sst.shape, 'loaded', round(time.time()-t_start,1), 's')

nt, ny, nx = sst.shape
# sea cells: finite on EVERY target day
sea = np.isfinite(sst).all(axis=0)
print('sea cells:', int(sea.sum()), 'of', ny*nx)

# hot mask
thr_day = thr_s[doy_t]              # (nt, ny, nx)
hot = (sst >= thr_day) & sea        # NaN comparisons -> False anyway; sea ensures land=0
print('hot days total:', int(hot.sum()), 'per-day active-cell counts min/max:',
      int(hot.sum(axis=(1,2)).min()), int(hot.sum(axis=(1,2)).max()))

# per-cell MHW: runs >=5, join gaps of 1-2 non-hot days
mhw = np.zeros_like(hot, dtype=bool)
n_events_cell = 0
for i in range(ny):
    for j in range(nx):
        h = hot[:, i, j]
        if not h.any():
            continue
        d = np.diff(h.astype(np.int8))
        starts = np.where(d == 1)[0] + 1
        ends = np.where(d == -1)[0]
        if h[0]: starts = np.r_[0, starts]
        if h[-1]: ends = np.r_[ends, nt-1]
        lens = ends - starts + 1
        keep = lens >= 5
        starts, ends = starts[keep], ends[keep]
        if len(starts) == 0:
            continue
        # join gaps of 1 or 2 days
        merged_s = [starts[0]]; merged_e = [ends[0]]
        for s_, e_ in zip(starts[1:], ends[1:]):
            if s_ - merged_e[-1] - 1 <= 2:
                merged_e[-1] = e_
            else:
                merged_s.append(s_); merged_e.append(e_)
        n_events_cell += len(merged_s)
        for s_, e_ in zip(merged_s, merged_e):
            mhw[s_:e_+1, i, j] = True

print('per-cell MHW pieces (after joining):', n_events_cell)
print('mhw mask days total:', int(mhw.sum()))
cell_counts = mhw.sum(axis=(1,2))
print('cells-in-MHW per day: min', int(cell_counts.min()), 'max', int(cell_counts.max()))

# regional: active = at least one sea cell in MHW
active = cell_counts > 0
print('active days:', int(active.sum()), 'of', nt)
# events = maximal runs of active
d = np.diff(active.astype(np.int8))
estarts = np.where(d == 1)[0] + 1; eends = np.where(d == -1)[0]
if active[0]: estarts = np.r_[0, estarts]
if active[-1]: eends = np.r_[eends, nt-1]
events = [(int(s), int(e)) for s, e in zip(estarts, eends)]
for s, e in events:
    print('EVENT', str(tgt_dates[s]), '->', str(tgt_dates[e]), f'({e-s+1} days)')
np.savez('/work/mhw_state.npz', mhw=mhw, active=active, sea=sea,
         events=np.array(events).reshape(-1,2) if events else np.zeros((0,2),int),
         tgt_dates=tgt_dates.astype('datetime64[D]').astype(int))
print('done, total time', round(time.time()-t_start,1), 's')