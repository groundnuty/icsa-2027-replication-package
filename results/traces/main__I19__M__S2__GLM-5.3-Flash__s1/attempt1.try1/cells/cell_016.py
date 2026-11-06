import numpy as np, pandas as pd, os, json
import netCDF4 as nc
import xarray as xr

src = xr.open_dataset("/data/icsa2027_data_20261101T090944Z/s2z/sst_s2.nc", engine="h5netcdf")
times = pd.DatetimeIndex(src["time"].values)
ti = np.where((times >= "2014-06-01") & (times <= "2014-08-31"))[0]
mhw = np.load("/work/mhw.npy"); sea = np.load("/work/sea.npy")

tsec = ((times[ti] - pd.Timestamp("1981-01-01")).total_seconds()).astype("int64")
assert np.all(tsec % 86400 == 0)
tsec32 = tsec.astype("int32")
lat32 = src["latitude"].values[182:242].astype("float32")
lon32 = src["longitude"].values[690:750].astype("float32")

p_nc = "/work/output/mhw_mask.nc"
dsout = nc.Dataset(p_nc, "w", format="NETCDF4")
dsout.title = "Marine heatwave (MHW) per-cell mask, Baltic Sea region, 2014-06-01 to 2014-08-31"
dsout.institution = "derived from CMEMS cmems_obs-sst_bal_phy-temp_my_l4_P1D-m"
dsout.source = "SST_BAL_SST_L4_REP_OBSERVATIONS_010_016 (DMI reprocessed L4 daily SST)"
dsout.comment = ("mhw=1 where the cell is inside a per-cell MHW (90th-percentile day-of-year threshold "
                 "from baseline 1992-2002, hot if SST >= threshold, runs >=5 consecutive hot days, "
                 "gaps <=2 days joined); mhw=0 otherwise, including land cells")
dsout.region = "lat 57.13-58.33 N, lon 22.79-23.99 E (bounds inclusive)"
dsout.copernicus_marine_product_id = "SST_BAL_SST_L4_REP_OBSERVATIONS_010_016"
dsout.copernicus_marine_dataset_id = "cmems_obs-sst_bal_phy-temp_my_l4_P1D-m"
dsout.createDimension("time", 92)
dsout.createDimension("latitude", 60)
dsout.createDimension("longitude", 60)
tv = dsout.createVariable("time", "i4", ("time",))
tv.units = "seconds since 1981-01-01"; tv.calendar = "proleptic_gregorian"
tv.standard_name = "time"; tv.long_name = "Time"; tv.axis = "T"
tv[:] = tsec32
latv = dsout.createVariable("latitude", "f4", ("latitude",))
latv.units = "degrees_north"; latv.standard_name = "latitude"; latv.long_name = "latitude"; latv.axis = "Y"
latv[:] = lat32
lonv = dsout.createVariable("longitude", "f4", ("longitude",))
lonv.units = "degrees_east"; lonv.standard_name = "longitude"; lonv.long_name = "longitude"; lonv.axis = "X"
lonv[:] = lon32
mv = dsout.createVariable("mhw", "u1", ("time", "latitude", "longitude"), zlib=True)
mv.long_name = "marine heatwave per-cell mask"
mv.flag_values = np.array([0, 1], dtype=np.uint8)
mv.flag_meanings = "not_in_mhw in_mhw"
mv.coordinates = "time latitude longitude"
mv[:] = mhw.astype(np.uint8)
dsout.close()
print("rewrote", p_nc, os.path.getsize(p_nc), "bytes")

# ---- verify by reopening (raw values + CF-decoded) ----
chk = nc.Dataset(p_nc, "r")
print("dims:", {k: len(v) for k, v in chk.dimensions.items()})
mv = chk["mhw"]
print("mhw dtype:", mv.dtype, "shape:", mv.shape)
arr = mv[:]
print("mhw sum:", int(arr.sum()), "unique:", np.unique(arr), "| identical to computed:", bool(np.array_equal(arr.astype(bool), mhw)))
print("time raw [0],[-1]:", chk["time"][0], chk["time"][-1], "| src raw:", tsec32[0], tsec32[-1])
print("time units:", chk["time"].units, chk["time"].calendar)
print("time decoded [0],[-1]:", nc.num2date(chk["time"][0], chk["time"].units, chk["time"].calendar),
      nc.num2date(chk["time"][-1], chk["time"].units, chk["time"].calendar))
dts = nc.num2date(chk["time"][:], chk["time"].units, chk["time"].calendar)
import cftime
want = pd.date_range("2014-06-01", "2014-08-31", freq="D")
got = pd.to_datetime([np.datetime64(x.isoformat()) for x in dts])
print("decoded times == target days exactly:", bool(np.array_equal(got.values, want.values)))
la, lo = chk["latitude"][:], chk["longitude"][:]
print("lat32 bit-identical:", bool(np.array_equal(la.view("u4"), lat32.view("u4"))),
      "lon32 bit-identical:", bool(np.array_equal(lo.view("u4"), lon32.view("u4"))))
print("lat/lon ranges:", float(la.min()), float(la.max()), "|", float(lo.min()), float(lo.max()))
print("land cells all 0:", bool(np.all(arr[:, ~sea] == 0)))
chk.close()

# cross-check with xarray/h5netcdf decode
dsv = xr.open_dataset(p_nc, engine="h5netcdf")
print(dsv)
dsv.close()
