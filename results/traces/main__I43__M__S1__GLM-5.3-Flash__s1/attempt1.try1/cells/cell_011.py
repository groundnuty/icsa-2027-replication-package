import h5py, numpy as np, time, json, os
from concurrent.futures import ThreadPoolExecutor
from datetime import date, timedelta

DIR='/data/icsa2027_data_20261101T090944Z/s1z'
ILAT=slice(438,498); ILON=slice(487,547)  # lat 62.26..63.44, lon 18.74..19.92

def load_one(fn):
    last_err = None
    for attempt in range(4):
        try:
            with h5py.File(f'{DIR}/sst_{fn}.nc','r') as f:
                a = f['analysed_sst'][0, ILAT, ILON]
            return np.asarray(a, dtype='float32')
        except Exception as e:
            last_err = e
            time.sleep(1.0 + attempt)
    raise RuntimeError(f'failed {fn}: {last_err}')

def daterange(d0, d1):
    out=[]; cur=d0
    while cur <= d1:
        out.append(cur); cur += timedelta(days=1)
    return out

base_dates = daterange(date(1991,12,27), date(2003,1,5))
targ_dates = daterange(date(2017,6,1),  date(2017,8,31))
print('baseline range n =', len(base_dates), base_dates[0], base_dates[-1])
print('target range n =', len(targ_dates), targ_dates[0], targ_dates[-1])

def load_all(dates, tag):
    fns = [d.strftime('%Y%m%d') for d in dates]
    t0=time.time()
    with ThreadPoolExecutor(16) as ex:
        arrs = list(ex.map(load_one, fns))
    cube = np.stack(arrs)  # (n, 60, 60) float32
    print(f'{tag}: {cube.shape} in {time.time()-t0:.1f}s, nan frac {np.isnan(cube).mean():.4f}')
    return cube

base_cube = load_all(base_dates, 'baseline')
targ_cube = load_all(targ_dates, 'target')

np.savez_compressed('/work/cubes.npz',
    base_cube=base_cube, targ_cube=targ_cube,
    base_dates=np.array([d.isoformat() for d in base_dates]),
    targ_dates=np.array([d.isoformat() for d in targ_dates]))
print('saved /work/cubes.npz', os.path.getsize('/work/cubes.npz')/1e6, 'MB')
