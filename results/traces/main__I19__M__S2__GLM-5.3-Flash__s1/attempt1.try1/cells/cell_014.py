import numpy as np, pandas as pd, os, json
import netCDF4 as nc
import xarray as xr

os.makedirs("/work/output", exist_ok=True)
mhw = np.load("/work/mhw.npy")
sea = np.load("/work/sea.npy")

src = xr.open_dataset("/data/icsa2027_data_20261101T090944Z/s2z/sst_s2.nc", engine="h5netcdf")
times = pd.DatetimeIndex(src["time"].values)
ti = np.where((times >= "2014-06-01") & (times <= "2014-08-31"))[0]
tdates = times[ti]
lat_vals = src["latitude"].values[182:242].astype("float64")
lon_vals = src["longitude"].values[690:750].astype("float64")

# ---- mhw_mask.nc ----
p_nc = "/work/output/mhw_mask.nc"
dsout = nc.Dataset(p_nc, "w", format="NETCDF4")
dsout.title = "Marine heatwave (MHW) per-cell mask, Baltic Sea region, 2014-06-01 to 2014-08-31"
dsout.institution = "derived from CMEMS cmems_obs-sst_bal_phy-temp_my_l4_P1D-m"
dsout.source = "SST_BAL_SST_L4_REP_OBSERVATIONS_010_016 (DMI reprocessed L4 daily SST)"
dsout.comment = "mhw=1 where cell is inside a per-cell MHW (90th pct day-of-year threshold from 1992-2002, >= comparison, runs >=5 d, gaps <=2 d joined); land and non-MHW cells 0"
dsout.region = "lat 57.13-58.33 N, lon 22.79-23.99 E (bounds inclusive)"
dsout.copernicus_marine_product_id = "SST_BAL_SST_L4_REP_OBSERVATIONS_010_016"
dsout.copernicus_marine_dataset_id = "cmems_obs-sst_bal_phy-temp_my_l4_P1D-m"
dsout.createDimension("time", 92)
dsout.createDimension("lat", 60)
dsout.createDimension("lon", 60)
tv = dsout.createVariable("time", "i8", ("time",))
tv.units = "days since 2014-06-01 00:00:00"; tv.calendar = "proleptic_gregorian"
tv.standard_name = "time"; tv.long_name = "time"; tv.axis = "T"
tv[:] = np.arange(92)
latv = dsout.createVariable("lat", "f8", ("lat",))
latv.units = "degrees_north"; latv.standard_name = "latitude"; latv.long_name = "latitude"; latv.axis = "Y"
latv[:] = lat_vals
lonv = dsout.createVariable("lon", "f8", ("lon",))
lonv.units = "degrees_east"; lonv.standard_name = "longitude"; lonv.long_name = "longitude"; lonv.axis = "X"
lonv[:] = lon_vals
mv = dsout.createVariable("mhw", "u1", ("time", "lat", "lon"), zlib=True)
mv.long_name = "marine heatwave per-cell mask"
mv.flag_values = np.array([0, 1], dtype=np.uint8)
mv.flag_meanings = "not_in_mhw in_mhw"
mv.coordinates = "time lat lon"
mv[:] = mhw.astype(np.uint8)
dsout.close()
print("wrote", p_nc, os.path.getsize(p_nc), "bytes")

# ---- report.json ----
report = {
    "region": {"lat_min": 57.13, "lat_max": 58.33, "lon_min": 22.79, "lon_max": 23.99},
    "baseline_analysed": {"start": "1992-01-01", "end": "2002-12-31"},
    "target_analysed": {"start": "2014-06-01", "end": "2014-08-31"},
    "events": [{"onset": "2014-07-24", "end": "2014-08-18"}],
    "complete": True,
    "caveats": ("Grid is 0.02 deg, so analysed cells (centres within the bounds) span lat 57.14-58.32, "
                "lon 22.80-23.98 (60x60 cells; 3301 are sea cells, i.e. finite SST on every target day; "
                "corner land cells are 0 in the mask). Pool statistics use only baseline years 1992-2002, "
                "but as prescribed, day-of-year pools additionally include SST from 1991-12-27..1991-12-31 "
                "and 2003-01-01..2003-01-05 (overflow days are pool values, not baseline days). Day 60 "
                "(29 February) has no pool of its own: its threshold and climatology are the mean of days "
                "59 and 61 before smoothing. A day is hot when SST (kelvin) >= threshold. The climatology "
                "was computed as prescribed but does not enter the MHW definition. Quantiles use "
                "MATLAB-default (Hyndman-Fan type 5, numpy method='hazen'). One regional MHW event found: "
                "2014-07-24..2014-08-18 (26 active days; cells inside a per-cell MHW range from 79 on the "
                "first day to 3269 at peak).")
}
p_js = "/work/output/report.json"
with open(p_js, "w") as fh:
    json.dump(report, fh, indent=2)
print("wrote", p_js, os.path.getsize(p_js), "bytes")

# ---- verification: reopen both files ----
chk = nc.Dataset(p_nc, "r")
print("dims:", {k: len(v) for k, v in chk.dimensions.items()})
mv = chk["mhw"]
print("mhw dtype:", mv.dtype, "shape:", mv.shape)
arr = mv[:]
print("mhw sum:", int(arr.sum()), "unique:", np.unique(arr))
print("time[0], time[-1]:", chk["time"][0], chk["time"][-1])
latr = chk["lat"][:]; lonr = chk["lon"][:]
print("lat[0], lat[-1]:", latr[0], latr[-1], "| lon[0], lon[-1]:", lonr[0], lonr[-1])
# compare against the computed mask
print("mask identical to computed:", bool(np.array_equal(arr.astype(bool), mhw)))
# land cells all zero?
print("land cells all 0:", bool(np.all(arr[:, ~sea] == 0)))
chk.close()
with open(p_js) as fh:
    rj = json.load(fh)
print("report keys:", list(rj.keys()))
print(json.dumps({k: rj[k] for k in ["region", "baseline_analysed", "target_analysed", "events", "complete"]}, indent=1))
