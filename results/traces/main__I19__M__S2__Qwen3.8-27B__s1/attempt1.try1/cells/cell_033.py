script = '''
import numpy as np
import xarray as xr
import os

PATH = '/data/icsa2027_data_20261101T090944Z/s2z/sst_s2.nc'
OUT = '/work/output'
M = np.load('/work/mhw.npz', allow_pickle=True)
Z = np.load('/work/interim.npz', allow_pickle=True)
mem = M['mem']
rlat = Z['rlat']; rlon = Z['rlon']

ds = xr.open_dataset(PATH, engine="h5netcdf")
lat_all = ds.latitude; lon_all = ds.longitude
tol = 1e-6
mlat = (lat_all.values.astype(np.float64) >= 57.13 - tol) & (lat_all.values.astype(np.float64) <= 58.33 + tol)
mlon = (lon_all.values.astype(np.float64) >= 22.79 - tol) & (lon_all.values.astype(np.float64) <= 23.99 + tol)
rlat_v = lat_all[mlat].values   # float32, dataset values
rlon_v = lon_all[mlon].values
t_all = ds.time
t_sel_v = t_all[int(np.searchsorted(t_all.values, np.datetime64('2014-06-01')))
                : int(np.searchsorted(t_all.values, np.datetime64('2014-08-31'))) + 1].values
assert len(rlat_v) == 60 and len(rlon_v) == 60 and len(t_sel_v) == 92
assert np.array_equal(rlat_v.astype(np.float64), rlat)
assert np.array_equal(rlon_v.astype(np.float64), rlon)
ds.close()

mask = mem.reshape(92, 60, 60).astype(np.uint8)
out = xr.Dataset(
    {"mhw": (("time", "lat", "lon"), mask,
             {"flag_values": [0, 1], "flag_meanings": "not_in_mhw in_mhw",
              "description": ("1 where the grid cell is inside a per-cell MHW (incl. 1-2 d gap "
                              "joining), 0 otherwise; land cells 0. Region lat 57.13-58.33N, "
                              "lon 22.79-23.99E; 2014-06-01..2014-08-31.")}},
    coords={
        "time": ("time", t_sel_v),
        "lat":  ("lat", rlat_v),
        "lon":  ("lon", rlon_v),
    },
)
out.attrs["description"] = ("Per-cell MHW membership mask, method: 1992-2002 baseline with +/-5 d "
                            "windows (1991-12-27..2003-01-05), Hazen (numpy method='hazen') 90th "
                            "percentile threshold and pool mean climatology per day-of-year, day 60 = "
                            "mean(59,61), 31-d centred wrap-around (366 d) smoothing, hot = SST >= "
                            "threshold, per-cell MHW = run >=5 hot days, runs separated by 1-2 non-hot "
                            "days joined. Dataset: cmems_obs-sst_bal_phy-temp_my_l4_P1D-m.")
out.to_netcdf(os.path.join(OUT, "mhw_mask.nc"))
print("rewritten")
'''
open('/work/write_out2.py','w').write(script)
import runpy
runpy.run_path('/work/write_out2.py', run_name='__main__')
