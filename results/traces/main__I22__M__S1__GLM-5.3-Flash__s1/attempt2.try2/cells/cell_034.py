import numpy as np, datetime as dt
W = '/work/work'
thr = np.load(f'{W}/thr.npy')
clim = np.load(f'{W}/clim.npy')
data = np.load(f'{W}/baseline_data.npy')
# find a sea cell: finite thr at day 152
mask_sea = np.isfinite(thr[152])
ys, xs = np.where(mask_sea)
print('sea cell example:', ys[0], xs[0])
y0, x0 = ys[0], xs[0]
print('thr raw->smoothed at (day153, cell):',
      f'{thr[152, y0, x0]:.4f}')
print('clim smoothed at same:', f'{clim[152, y0, x0]:.4f}')
# threshold range for this cell across year
print('cell threshold: min', thr[:, y0, x0].min(), 'max', thr[:, y0, x0].max())
print('cell clim: min', clim[:, y0, x0].min(), 'max', clim[:, y0, x0].max())
# plot-free check of seasonal shape: monthly means of clim
for m in range(1, 13):
    mm = [152 + i for i in range(0, 1)]
# seasonal curve summary every 30 days
for s in [1, 32, 61, 92, 122, 153, 183, 214, 245, 275, 306, 336, 366]:
    print(f'day {s:3d}: clim {clim[s-1, y0, x0]:7.3f}  thr {thr[s-1, y0, x0]:7.3f}')
