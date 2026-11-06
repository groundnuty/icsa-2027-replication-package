script = r'''
import numpy as np, datetime as dt, os, json, h5py
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

epoch = dt.date(1981,1,1)
# verify epoch math against actual file time values for 3 sample days
for d in (tdays[0], tdays[45], tdays[-1]):
    with h5py.File("/data/icsa2027_data_20261101T090944Z/s1z/sst_"+d.strftime("%Y%m%d")+".nc","r") as f:
        tv = f["time"][0]
    calc = float((d - epoch).days * 86400)
    print(d, "file time:", int(tv), "computed:", calc, "match:", int(tv) == calc)
tvals = np.array([(d - epoch).days * 86400.0 for d in tdays])

with h5py.File("/data/icsa2027_data_20261101T090944Z/s1z/sst_20130601.nc","r") as f:
    lat = f["latitude"][218:278].astype(np.float64)
    lon = f["longitude"][601:661].astype(np.float64)

os.makedirs("/work/output", exist_ok=True)
with Dataset("/work/output/mhw_mask.nc", "w", format="NETCDF4") as nc:
    nc.createDimension("time", 92); nc.createDimension("lat", 60); nc.createDimension("lon", 60)
    tv = nc.createVariable("time", "f8", ("time",))
    tv.units = "seconds since 1981-01-01"; tv.calendar = "proleptic_gregorian"
    tv.standard_name = "time"; tv.long_name = "Time"; tv.axis = "T"
    tv[:] = tvals
    yv = nc.createVariable("lat", "f4", ("lat",))
    yv.units = "degrees_north"; yv.standard_name = "latitude"; yv.axis = "Y"
    yv[:] = lat.astype(np.float32)
    xv = nc.createVariable("lon", "f4", ("lon",))
    xv.units = "degrees_east"; xv.standard_name = "longitude"; xv.axis = "X"
    xv[:] = lon.astype(np.float32)
    mv = nc.createVariable("mhw", "u1", ("time","lat","lon"), zlib=True, complevel=4)
    mv.long_name = "marine heatwave mask (cell inside a per-cell MHW)"
    mv.flag_values = np.array([0,1], np.uint8); mv.flag_meanings = "not_in_mhw in_mhw"
    mv.comment = ("Per-cell marine heatwave mask from cmems_obs-sst_bal_phy-temp_my_l4_P1D-m; "
                  "threshold = 31-day circular-smoothed day-of-year 90th percentile (MATLAB quantile "
                  "default / hazen type 5) of 1992-2002 baseline +/-5-day pools; runs >=5 hot days, "
                  "gaps <=2 days joined; region 57.85-59.05N 21.01-22.21E; target 2013-06-01..2013-08-31.")
    mv[:] = mhw
    nc.Conventions = "CF-1.8"
    nc.title = "Marine heatwave mask, Baltic Sea region, Jun-Aug 2013"

caveat = ("Hot-day runs were searched only within the target period, as specified, so a physical event "
          "beginning in late May 2013 would be reported with onset 2013-06-01 (context: 356 of 3301 sea "
          "cells were at or above threshold on 2013-05-31 and 361 on 2013-05-30, though no cell had >=5 "
          "consecutive hot days ending 2013-05-31). Baseline pools include the window-extension days "
          "1991-12-27..1991-12-31 and 2003-01-01..2003-01-05 required by the method; all pools were "
          "complete (121 values, 63 for 29 Feb) and all 3301 region sea cells had finite SST on every "
          "target day, so missing data did not affect the result.")
report = {
    "region": {"lat_min": 57.85, "lat_max": 59.05, "lon_min": 21.01, "lon_max": 22.21},
    "baseline_analysed": {"start": "1992-01-01", "end": "2002-12-31"},
    "target_analysed": {"start": "2013-06-01", "end": "2013-08-31"},
    "events": events,
    "complete": True,
    "caveats": caveat,
}
with open("/work/output/report.json","w") as f:
    json.dump(report, f, indent=2)
print(json.dumps(report, indent=2))
'''
open("/work/write_out2.py","w").write(script)
import subprocess
r = subprocess.run(["python","/work/write_out2.py"], capture_output=True, text=True, timeout=1800)
print(r.stdout); print("STDERR:", r.stderr[-1500:]); print("rc:", r.returncode)
