import numpy as np, time
W = '/work/work'
thr_raw = np.load(f'{W}/thr_raw.npy')
clim_raw = np.load(f'{W}/clim_raw.npy')

def smooth366(a):
    S = np.zeros_like(a)
    for k in range(-15, 16):
        S += np.roll(a, -k, axis=0)
    return S / 31.0

t0 = time.time()
thr = smooth366(thr_raw)
clim = smooth366(clim_raw)
print(f'smoothing: {time.time()-t0:.2f} s')
# land cells remain NaN
nan_t = np.isnan(thr)
print('NaN cells after smoothing:', nan_t.sum(), 'per day constant:', np.all(nan_t == nan_t[0]))
# sea cell stats
finite_cells = ~nan_t[0]
print('cells with valid threshold:', finite_cells.sum(), 'of', 3600)
np.save(f'{W}/thr.npy', thr)
np.save(f'{W}/clim.npy', clim)
print('threshold range (sea cells):', np.nanmin(thr), np.nanmax(thr))
print('climatology range (sea cells):', np.nanmin(clim), np.nanmax(clim))
# spot check: threshold at day 153 (June 2) for a sea cell vs raw
s = 152
print('thr smoothed[152, :3, :3]:', thr[152, :3, :3].ravel()[:3], 'raw:', thr_raw[152, :3, :3].ravel()[:3])
