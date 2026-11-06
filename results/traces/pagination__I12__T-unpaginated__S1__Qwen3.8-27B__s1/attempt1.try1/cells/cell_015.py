import numpy as np

thr_raw = np.load('/tmp/thr_raw.npy')
clim_raw = np.load('/tmp/clim_raw.npy')

def smooth31(raw):
    ext = np.concatenate([raw[-15:], raw, raw[:15]], axis=0)      # (396, 3600)
    win = np.lib.stride_tricks.sliding_window_view(ext, 31, axis=0)  # (366, 3600, 31)
    return win.mean(axis=2)

thr_sm = smooth31(thr_raw)
clim_sm = smooth31(clim_raw)
print('shapes:', thr_sm.shape, clim_sm.shape)

# manual verification for one cell: doy 153 (idx 152)
c = 0
idxs = [(152 + k) % 366 for k in range(-15, 16)]
manual = thr_raw[idxs, c].mean()
print('manual vs vec (cell0, doy153):', manual, thr_sm[152, c], np.allclose(manual, thr_sm[152, c]))
# check wrapping at doy 1 (idx 0): days -15..15 mod 366 = 351..365, 0..15
idxs0 = [d % 366 for d in range(-15, 16)]
manual0 = thr_raw[idxs0, c].mean()
print('wrap check:', np.allclose(manual0, thr_sm[0, c]))
# day 60 raw = mean(59,61)
print('doy60 raw == mean(59,61):', np.allclose(thr_raw[59], 0.5*(thr_raw[58]+thr_raw[60])))

np.save('/tmp/thr_sm.npy', thr_sm)
np.save('/tmp/clim_sm.npy', clim_sm)

t = np.load('/tmp/tgt.npz'); tgt = t['arr']
finite_tgt = np.all(np.isfinite(tgt), axis=0).reshape(3600)
sea = np.where(finite_tgt)[0]
print('sea cells:', len(sea), 'NaN smoothed (sea):', bool(np.isnan(thr_sm[:, sea]).any()), bool(np.isnan(clim_sm[:, sea]).any()))
cs = sea[0]
print('sample cell', cs, 'flat', cs//60, cs%60)
for dd2 in (153, 198, 244):
    print(f'doy {dd2}: clim_raw={clim_raw[dd2-1,cs]:.3f} thr_raw={thr_raw[dd2-1,cs]:.3f} | clim_sm={clim_sm[dd2-1,cs]:.3f} thr_sm={thr_sm[dd2-1,cs]:.3f}')
print('target SST 2009-06-01 sample:', tgt[0, cs//60, cs%60])
print('Jun1 thr_sm (C) min/median/max over sea:', (np.nanmin(thr_sm[152,sea])-273.15), (np.nanmedian(thr_sm[152,sea])-273.15), (np.nanmax(thr_sm[152,sea])-273.15))