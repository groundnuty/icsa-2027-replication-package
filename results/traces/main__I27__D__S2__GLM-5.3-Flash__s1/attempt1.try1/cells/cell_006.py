import numpy as np, datetime, warnings, os

data = np.load('/work/region_data.npz')
sst = data['sst']; days = data['days']; lat = data['lat']; lon = data['lon']
dates = days.tolist()   # datetime.date objects (datetime64[D])
ords = np.array([x.toordinal() for x in dates])
doys = np.array([datetime.date(2000, x.month, x.day).timetuple().tm_yday for x in dates])

print('check doys:', doys[ords==datetime.date(1992,1,1).toordinal()],
      doys[ords==datetime.date(1992,2,28).toordinal()],
      doys[ords==datetime.date(1992,2,29).toordinal()],
      doys[ords==datetime.date(1992,3,1).toordinal()],
      doys[ords==datetime.date(1993,3,1).toordinal()],
      doys[ords==datetime.date(2002,12,31).toordinal()])

base_idx = np.where((ords >= datetime.date(1992,1,1).toordinal()) & (ords <= datetime.date(2002,12,31).toordinal()))[0]
print('baseline dates:', len(base_idx), days[base_idx[0]], days[base_idx[-1]])
o2i = {int(o):i for i,o in enumerate(ords)}

pool = [None]*367
for bi in base_idx:
    d0 = int(doys[bi])
    if d0 == 60:
        continue
    o = int(ords[bi])
    if pool[d0] is None: pool[d0] = []
    for off in range(-5,6):
        j = o2i.get(o+off)
        if j is not None: pool[d0].append(j)

sizes = np.array([len(p) if p is not None else -1 for p in pool[1:]])
print('pool sizes: min', sizes[sizes>0].min(), 'max', sizes.max(), 'missing idx (doy-1):', np.where(sizes<0)[0])
print('pool size doy1,59,61,366:', sizes[0], sizes[58], sizes[60], sizes[365])
p1 = sorted(set(days[np.array(pool[1])].tolist()))
p366 = sorted(set(days[np.array(pool[366])].tolist()))
print('doy1 window dates:', np.datetime64(p1[0]), '->', np.datetime64(p1[-1]))
print('doy366 window dates:', np.datetime64(p366[0]), '->', np.datetime64(p366[-1]))

flat = sst.astype(np.float64).reshape(len(days), -1)
NT, NC = flat.shape
thr_raw = np.full((366, NC), np.nan)
clim_raw = np.full((366, NC), np.nan)
with warnings.catch_warnings():
    warnings.simplefilter('ignore', RuntimeWarning)
    for d in range(1, 367):
        if d == 60: continue
        vals = flat[np.array(pool[d])]
        thr_raw[d-1] = np.nanpercentile(vals, 90, axis=0, method='hazen')
        clim_raw[d-1] = np.nanmean(vals, axis=0)
thr_raw[59] = 0.5*(thr_raw[58] + thr_raw[60])
clim_raw[59] = 0.5*(clim_raw[58] + clim_raw[60])
print('raw done. thr range:', np.nanmin(thr_raw), np.nanmax(thr_raw))

def circ_smooth(a):
    ext = np.concatenate([a[-15:], a, a[:15]], axis=0)
    cs = np.zeros((ext.shape[0]+1,) + a.shape[1:])
    np.cumsum(ext, axis=0, out=cs[1:])
    return (cs[31:] - cs[:-31]) / 31.0

thr = circ_smooth(thr_raw)
clim = circ_smooth(clim_raw)
print('smooth shapes', thr.shape, clim.shape)
rng = np.random.default_rng(0)
j, c = int(rng.integers(0,366)), int(rng.integers(0,NC))
idxs = [(j-15+k) % 366 for k in range(31)]
print('check smooth mid:', thr[j,c], thr_raw[idxs,c].mean())
k = 3
idxs = [(k-15+q) % 366 for q in range(31)]
print('check smooth wrap k=3:', thr[k,c], thr_raw[idxs,c].mean())
np.savez_compressed('/work/clim.npz', thr=thr, clim=clim, thr_raw=thr_raw, clim_raw=clim_raw)
print('nan cells in thr:', np.isnan(thr).any(axis=0).sum())
print('clim sample cell:', clim[[151,181,212,243], 0])
print('thr  sample cell:', thr[[151,181,212,243], 0])
