import h5py, numpy as np, os, datetime as dt
BASE = "/data/icsa2027_data_20261101T090944Z/s1z"
epoch = dt.datetime(1981,1,1)
ok = True
for f, expect in [("sst_19911227.nc","1991-12-27"),("sst_19920229.nc","1992-02-29"),("sst_20021231.nc","2002-12-31"),
                  ("sst_20030105.nc","2003-01-05"),("sst_20040601.nc","2004-06-01"),("sst_20040831.nc","2004-08-31"),
                  ("sst_20040715.nc","2004-07-15")]:
    with h5py.File(os.path.join(BASE,f), "r") as hf:
        t = hf["time"][()]
        d = (epoch + dt.timedelta(seconds=float(t[0]))).date()
    status = "OK" if d.isoformat()==expect else f"MISMATCH {d}"
    ok &= (d.isoformat()==expect)
    print(f, status)
print("all time coords match filenames:", ok)
