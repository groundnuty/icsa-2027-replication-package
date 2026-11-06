import xarray as xr, numpy as np
M = np.load('/work/mhw.npz', allow_pickle=True)
m = xr.open_dataset('/work/output/mhw_mask.nc', engine="h5netcdf").mhw.values
col_active = np.where(M['mem'][53])[0]
for c in [int(col_active[0]), int(col_active[-1]), int(col_active[len(col_active)//2])]:
    r, col = divmod(c, 60)
    SRC = "/data/icsa2027_data_20261101T090944Z/s2z/sst_s2.nc"
    src = xr.open_dataset(SRC, engine="h5netcdf")
    latv = float(np.load('/work/interim.npz')['rlat'][r]); lonv = float(np.load('/work/interim.npz')['rlon'][col])
    li = int(np.argmin(np.abs(src.latitude.values.astype(np.float64) - latv)))
    lo = int(np.argmin(np.abs(src.longitude.values.astype(np.float64) - lonv)))
    ti = int(np.searchsorted(src.time.values, np.datetime64("2014-07-24")))
    sst = float(src.analysed_sst[ti, li, lo].values)
    thr_s = M['thr_s']
    print(f"cell({r},{col}) lat={latv} lon={lonv}: mask={m[53,r,col]} sst={sst:.4f}K thr(153)={thr_s[152,c]:.4f}K hot={bool(sst >= thr_s[152,c])}")
    src.close()
