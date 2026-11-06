import numpy as np, datetime, warnings
from numpy.lib.stride_tricks import sliding_window_view

data = np.load('/work/region_data.npz')
sst = data['sst']; days = data['days']; lat = data['lat']; lon = data['lon']
dates = [d.date() for d in days.tolist()]
ords = np.array([x.toordinal() for x in dates])
doys = np.array([datetime.date(2000, x.month, x.day).timetuple().tm_yday for x in dates])  # leap-year calendar: Feb29=60, Dec31=366

# sanity of doy mapping
import calendar
def chk(y,m,dd):
    return datetime.date(y,m,dd)
print('check doys:', doys[ords==datetime.date(1992,1,1).toordinal()],
      doys[ords==datetime.date(1992,2,28).toordinal()],
      doys[ords==datetime.date(1992,2,29).toordinal()],
      doys[ords==datetime.date(1992,3,1).toordinal()],
      doys[ords==datetime.date(1993,3,1).toordinal()],
      doys[ords==datetime.date(2002,12,31).toordinal()])

base_idx = np.where((ords >= datetime.date(1992,1,1).toordinal()) & (ords <= datetime.date(2002,12,31).toordinal()))[0]
print('baseline dates:', len(base_idx), str(days[base_idx[0]]), str(days[base_idx[-1]]))
o2i = {int(o):i for i,o in enumerate(ords)}

pool = [None]*367
for bi in base_idx:
    d0 = int(doys[bi])
    if d0 == 60:   # 29 Feb: no pool of its own; its values enter neighbours' windows naturally
        continue
    o = int(ords[bi])
    if pool[d0] is None: pool[d0] = []
    for off in range(-5,6):
        j = o2i.get(o+off)
        if j is not None: pool[d0].append(j)

sizes = np.array([len(p) if p is not None else -1 for p in pool[1:]])
print('pool sizes: min', sizes[sizes>0].min(), 'max', sizes.max(), 'missing (should be only idx59=doy60):', np.where(sizes<0)[0])
print('pool size doy1,59,61,366:', sizes[0], sizes[58], sizes[60], sizes[365])
# verify pool windows at edges
p1 = sorted(set(days[np.array(pool[1])].tolist()))
p366 = sorted(set(days[np.array(pool[366])].tolist()))
print('doy1 window dates:', str(np.datetime64(p1[0],'D')), '->', str(np.datetime64(p1[-1],'D')))
print('doy366 window dates:', str(np.datetime64(p366[0],'D')), '->', str(np.datetime64(p366[-1],'D')))

flat = sst.astype(np.float64).reshape(len(days), -1)   # float64
NT, NC = flat.shape
thr_raw = np.full((366, NC), np.nan)
clim_raw = np.full((366, NC), np.nan)
with warnings.catch_warnings():
    warnings.simplefilter('ignore', RuntimeWarning)
    for d in range(1, 367):
        if d == 60: continue
        vals = flat[np.array(pool[d])]           # (n, 3600)
        thr_raw[d-1] = np.nanpercentile(vals, 90, axis=0, method='hazen')
        clim_raw[d-1] = np.nanmean(vals, axis=0)
# fill doy 60 (index 59) with mean of doys 59 and 61
thr_raw[59] = 0.5*(thr_raw[58] + thr_raw[60])
clim_raw[59] = 0.5*(clim_raw[58] + clim_raw[60])
print('raw done. thr range (finite):', np.nanmin(thr_raw), np.nanmax(thr_raw))

def circ_smooth(a):  # a: (366, ...) centred 31-day unweighted moving mean, wraps mod 366
    ext = np.concatenate([a[-15:], a, a[:15]], axis=0)
    cs = np.zeros((ext.shape[0]+1,) + a.shape[1:])
    np.cumsum(ext, axis=0, out=cs[1:])
    return (cs[31:] - cs[:-31]) / 31.0

thr = circ_smooth(thr_raw)
clim = circ_smooth(clim_raw)
print('smooth shapes', thr.shape, clim.shape)
# verify smoothing manually at a random point incl. wraparound
rng = np.random.default_rng(0)
j, c = rng.integers(0,366), rng.integers(0,NC)
idxs = [(j-15+k) % 366 for k in range(31)]
print('check thr smooth:', thr[j,c], thr_raw[idxs,c].mean())
k = 3  # near start -> wraps to end
idxs = [(k-15+q) % 366 for q in range(31)]
print('check wrap k=3:', thr[k,c], thr_raw[idxs,c].mean())
np.savez_compressed('/work/clim.npz', thr=thr, clim=clim, thr_raw=thr_raw, clim_raw=clim_raw)
print('nan cells in thr (land?):', np.isnan(thr).any(axis=0).sum())
