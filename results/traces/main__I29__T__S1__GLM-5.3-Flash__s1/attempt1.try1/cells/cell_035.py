import numpy as np, datetime
tgt = np.load('target.npy').astype(np.float64)
thresh_raw = np.load('thresh_raw.npy'); thresh = np.load('thresh.npy')
clim_raw = np.load('clim_raw.npy'); clim = np.load('clim.npy')
i,j = 5,5
# raw threshold at doy 153..162 (0-based 152..161)
print('raw thresh d153-162 (cell 5,5):', thresh_raw[152:162, i, j].round(3))
print('smo  thresh d153-162 (cell 5,5):', thresh[152:162, i, j].round(3))
print('raw clim  d153-162 (cell 5,5):', clim_raw[152:162, i, j].round(3))
print('smo  clim  d153-162 (cell 5,5):', clim[152:162, i, j].round(3))
# sanity check the raw threshold manually for a cell: doy 153 pool
doy_ext = np.load('doy_ext.npy').astype(int)
base_ext = np.load('base_ext.npy')
idx = np.where(np.abs(doy_ext-153)<=5)[0]
pool = base_ext[idx][:, i, j]
print('doy153 pool size (cell 5,5):', len(pool), 'finite:', np.isfinite(pool).sum())
print('manual hazen p90:', np.percentile(pool[np.isfinite(pool)], 90, method='hazen'))
print('nanpercentile:  ', np.nanpercentile(pool, 90, method='hazen'))
print('mean:', np.nanmean(pool))
# climatology vs raw threshold relationship at mid-summer day
print('raw thresh d183 (cell5,5):', thresh_raw[182,i,j], ' raw clim d183:', clim_raw[182,i,j])
# what fraction of pool is >= raw thresh? (should be ~10% of finite values)
fin = pool[np.isfinite(pool)]
print('frac pool >= p90:', (fin >= np.percentile(fin,90,method='hazen')).mean())
