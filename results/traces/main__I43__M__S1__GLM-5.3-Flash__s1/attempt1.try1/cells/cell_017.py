import numpy as np
z = np.load('/work/clim.npz')
a = z['clm_s'][:, 0]
# day 1 (idx 0): offsets -15..+15 -> idx (0-15)%366=351 .. 365, then 0..15
idxs = [(0+off) % 366 for off in range(-15,16)]
print('n idx:', len(idxs), 'first/last:', idxs[0], idxs[-1])
print('day1: %.6f vs manual %.6f' % (a[0], a[idxs].mean()))
# day 366 (idx 365): idx 350..364, 365, 0..14
idxs2 = [(365+off) % 366 for off in range(-15,16)]
print('day366: %.6f vs manual %.6f' % (a[365], a[idxs2].mean()))
# day 60 (idx 59)
idxs3 = [(59+off) % 366 for off in range(-15,16)]
print('day60: %.6f vs manual %.6f' % (a[59], a[idxs3].mean()))
