script = r'''
import numpy as np, datetime as dt, os, json
from netCDF4 import Dataset

work = "/work"
mhw = np.load(work+"/mhw_mask.npy")
tf = np.load(work+"/target_finite.npy")
with open(work+"/events.json") as f:
    events = json.load(f)
data32 = np.concatenate([np.load(work+"/cache/"+b, mmap_mode="r") for b in sorted(os.listdir(work+"/cache"))], axis=0)
start = dt.date(1991,12,27)
dates = [start + dt.timedelta(days=i) for i in range(data32.shape[0])]
ti0 = dates.index(dt.date(2013,6,1)); ti1 = dates.index(dt.date(2013,8,31))
tdays = dates[ti0:ti1+1]

# coordinates exactly as stored in the dataset
with h5py_or_xr() if False else __import__("h5py").File("/data/icsa2027_data_20261101T090944Z/s1z/sst_20130601.nc","r") as f:
    lat = f["latitude"][218:278].astype(np.float64)
    lon = f["longitude"][601:661].astype(np.float64)
    tsec = f["time"][:]  # seconds since 1981-01-01 (int)
assert len(tdays) == 92 and mhw.shape == (92,60,60)
# time values must match the target dates
import cftime
chk = cftime.num2date(tsec[0] if False else 0, "seconds since 1981-01-01")

os.makedirs("/work/output", exist_ok=True)
with Dataset("/work/output/mhw_mask.nc", "w", format="NETCDF4") as nc:
    nc.createDimension("time", 92)
    nc.createDimension("lat", 60)
    nc.createDimension("lon", 60)
    tv = nc.createVariable("time", "f8", ("time",))
    tv.units = "seconds since 1981-01-01"; tv.calendar = "proleptic_gregorian"
    tv.standard_name = "time"; tv.long_name = "Time"; tv.axis = "T"
    tv[:] = np.asarray(tsec, dtype="f8")
    yv = nc.createVariable("lat", "f4", ("lat",))
    yv.units = "degrees_north"; yv.standard_name = "latitude"; yv.axis = "Y"
    yv[:] = lat.astype(np.float32)
    xv = nc.createVariable("lon", "f4", ("lon",))
    xv.units = "degrees_east"; xv.standard_name = "longitude"; xv.axis = "X"
    xv[:] = lon.astype(np.float32)
    mv = nc.createVariable("mhw", "u1", ("time","lat","lon"), zlib=True, complevel=4)
    mv.long_name = "marine heatwave mask (cell inside a per-cell MHW)"
    mv.units = "1"
    mv.flag_values = np.array([0,1], np.uint8)
    mv.flag_meanings = "not_in_mhw in_mhw"
    mv.comment = ("Per-cell marine heatwave mask for the Baltic Sea L4 daily SST "
                  "dataset cmems_obs-sst_bal_phy-temp_my_l4_P1D-m; threshold = 31-day "
                  "circular-smoothed day-of-year 90th percentile (MATLAB quantile / hazen type 5), "
                  "baseline 1992-2002; runs >=5 days, gaps <=2 days joined; target 2013-06-01..2013-08-31.")
    mv[:] = mhw
    nc.Conventions = "CF-1.8"
    nc.title = "Marine heatwave mask, Baltic Sea region, Jun-Aug 2013"

# ---- report.json ----
caveat = ("Hot-day runs were searched only within the target period, as specified, so a physical event "
          "beginning in late May 2013 would be reported with onset 2013-06-01 (context: 356 of 3301 sea "
          "cells were above threshold on 2013-05-31 and 361 on 2013-05-30, but no cell had >=5 consecutive "
          "hot days ending 2013-05-31). Baseline pools additionally contain the window-extension days "
          "1991-12-27..1991-12-31 and 2003-01-01..2003-01-05 required by the method; every pool was complete "
          "(121 values; 63 for 29 Feb) and all 3301 region sea cells had complete SST over the target period, "
          "so missing data did not affect the result.")
report = {
    "region": {"lat_min": 57.85, "lat_max": 59.05, "lon_min": 21.01, "lon_max": 22.21},
    "baseline_analysed": {"start": "1992-01-01", "end": "2002-12-31"},
    "target_analysed": {"start": "2013-06-01", "end": "2013-08-31"},
    "events": events,
    "complete": True,
    "caveats": caveat,
}
with open("/work/output/report.json", "w") as f:
    json.dump(report, f, indent=2)
print(json.dumps(report, indent=2))
'''
# small helper shim used above is not needed; rewrite cleanly without it
script = script.replace("with h5py_or_xr() if False else __import__(\"h5py\").File", "with __import__(\"h5py\").File")
script = script.replace("import cftime\nchk = cftime.num2date(tsec[0] if False else 0, \"seconds since 1981-01-01\")", "")
open("/work/write_out.py","w").write(script)
import subprocess
r = subprocess.run(["python","/work/write_out.py"], capture_output=True, text=True, timeout=1800)
print(r.stdout); print("STDERR:", r.stderr[-1500:]); print("rc:", r.returncode)
