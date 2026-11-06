import numpy as np, xarray as xr
ds = xr.open_dataset('/work/sst_s2.nc', engine='h5netcdf')
sst_b = np.load('/work/sst_b.npy')
bd = np.arange('1991-12-27', '2003-01-06', dtype='datetime64[D]')
for lab, i in [('1992-01-15', 19), ('1992-04-15', 110), ('1992-06-27', 183), ('1992-08-01', 218),
               ('1997-07-15', 2012), ('2002-07-01', 3843), ('2003-01-01', 4021)]:
    a = sst_b[i]
    print('%s  K: %.2f/%.2f/%.2f  degC: %.2f/%.2f/%.2f' %
          (lab, np.nanmin(a), np.nanmean(a), np.nanmax(a), np.nanmin(a)-273.15, np.nanmean(a)-273.15, np.nanmax(a)-273.15))

L0, L1, O0, O1 = 545, 604, 721, 780
sst_t = ds['analysed_sst'].isel(time=slice(13665, 13757), latitude=slice(L0, L1+1), longitude=slice(O0, O1+1)).values.astype(np.float64)
for lab, i in [('2019-06-01', 0), ('2019-07-16', 45), ('2019-08-31', 91)]:
    a = sst_t[i]
    print('%s  K: %.2f/%.2f/%.2f  degC: %.2f/%.2f/%.2f' %
          (lab, np.nanmin(a), np.nanmean(a), np.nanmax(a), np.nanmin(a)-273.15, np.nanmean(a)-273.15, np.nanmax(a)-273.15))

thr_s = np.load('/work/thr_s.npy')
clm_s = np.load('/work/clm_s.npy')
bd2 = np.arange('1991-12-27', '2003-01-06', dtype='datetime64[D]')
bmonths = bd2.astype('datetime64[M]').astype(int) % 12 + 1
bdays = (bd2 - bd2.astype('datetime64[M]')).astype(int) + 1
yrs = bd2.astype('datetime64[Y]').astype(int) + 1970
leap = ((yrs % 4 == 0) & ((yrs % 100 != 0) | (yrs % 400 == 0)))
cump = np.array([0,31,59,90,120,151,181,212,243,273,304,334])
bdoy = cump[bmonths-1] + bdays + (leap & (bmonths > 2)).astype(int)
# raw June-27 pool values for cell (30,30) across 1992-2002
per = [i for i in range(NT2:=sst_b.shape[0]) if abs(bdoy[i] - 178) <= 0 or False]
offs = []
for o in range(-5, 6):
    nd = bd2 + np.timedelta64(o, 'D')
    for idx in np.flatnonzero(bdoy == 178):
        if bd2[0] <= nd[idx] <= bd2[-1]: offs.append(idx + o)
offs = sorted(set(offs))
vals = sst_b[offs, 30, 30]
print('cell(30,30) pool doy178: n=%d finite=%d degC %.2f..%.2f mean %.2f' %
      (len(vals), np.isfinite(vals).sum(), np.nanmin(vals)-273.15, np.nanmax(vals)-273.15, np.nanmean(vals)-273.15))
print('  years:', [str(bd2[0] + np.timedelta64(int(x), "D"))[:7] for x in offs])
