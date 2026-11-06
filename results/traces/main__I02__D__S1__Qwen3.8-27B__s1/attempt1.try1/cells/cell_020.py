import numpy as np
S_tgt = np.load('/work/S_tgt.npy')
thr_s = np.load('/work/thr_s.npy'); clim_s = np.load('/work/clim_s.npy')
tgt_doy = np.load('/work/tgt_doy.npy')
fin_mask = np.isfinite(S_tgt).all(axis=0)   # (60,60)
sea_cells = np.flatnonzero(fin_mask.ravel()) # flat indices, r*60+c
print("sea cells:", sea_cells.size, "of 3600")
land_cells = np.flatnonzero(~fin_mask.ravel())
print("land cells:", land_cells.size)
cr = np.load('/work/coords.npz'); lat, lon = cr['lat'], cr['lon']
# where are the land cells? (row, col)
rr, cc = np.unravel_index(land_cells, (60,60))
print("land row range:", rr.min(), rr.max(), "col range:", cc.min(), cc.max())
print("sample land (lat,lon):", [(round(float(lat[r]),2), round(float(lon[c]),2)) for r,c in list(zip(rr,cc))[:8]])
print("sample sea  (lat,lon):", [(round(float(lat[r]),2), round(float(lon[c]),2)) for r,c in list(zip(rr,cc))[-4:]])

td = np.unique(tgt_doy)
nanpost = ~np.isfinite(thr_s)
sea_nan_tgt = [c for c in sea_cells if nanpost[td, c].any()]
print("sea cells with NaN thr on any TARGET doy:", len(sea_nan_tgt), sea_nan_tgt[:20])
sea_nan_any = [c for c in sea_cells if nanpost[:, c].any()]
print("sea cells with NaN thr on any doy (winter gaps ok):", len(sea_nan_any))
land_nan_tgt = [c for c in land_cells if ~nanpost[td, c].all()]
print("land cells with some finite thr on target doys (irrelevant):", len(land_nan_tgt))
sea_nan_clim = [c for c in sea_cells if (~np.isfinite(clim_s[td, c])).any()]
print("sea cells with NaN clim on target doys:", len(sea_nan_clim))

np.save('/work/sea_cells.npy', sea_cells)
np.save('/work/land_cells.npy', land_cells)
print("SAVED sea/land")
