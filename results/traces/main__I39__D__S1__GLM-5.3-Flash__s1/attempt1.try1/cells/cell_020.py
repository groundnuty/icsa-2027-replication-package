import numpy as np, time

thr_raw = np.load('/work/thr_raw.npy'); clim_raw = np.load('/work/clim_raw.npy')
N = 366
def circ_smooth(a):
    out = np.zeros_like(a)
    for off in range(-15, 16):
        out += np.roll(a, off, axis=0)
    return out / 31.0

t0 = time.time()
thr = circ_smooth(thr_raw.copy())
clim = circ_smooth(clim_raw.copy())
print('smoothing done %.1fs' % (time.time()-t0))
print('nan in smoothed among sea cells: thr', int(np.isnan(thr[:, :]).sum()), 'clim', int(np.isnan(clim).sum()))
# sample values at a sea cell for doy 200
cell = (200, 15, 15)
print('raw thr doy200 cell:', thr_raw[cell], '-> smoothed:', thr[cell])
print('raw clim doy200 cell:', clim_raw[cell], '-> smoothed:', clim[cell])
np.save('/work/thr.npy', thr); np.save('/work/clim.npy', clim)
print('saved thr.npy, clim.npy')
