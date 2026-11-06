import h5py, numpy as np, os, datetime as dt
BASE = "/data/icsa2027_data_20261101T090944Z/s1z"
with h5py.File(os.path.join(BASE,"sst_19920229.nc"), "r") as hf:
    t = hf["time"][()]
    attrs = dict(hf["time"].attrs)
    print("raw:", t, attrs.get("units"), attrs.get("calendar"))
# decode: probably "days since 1990-01-01"
if "units" in attrs:
    units = str(attrs["units"])
    epoch = dt.date(1990,1,1)  # guess; parse properly below
    import re
    m = re.match(r"days since (\d{4})-(\d{2})-(\d{2})", units)
    epoch = dt.date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
    print("epoch:", epoch, "decoded:", [epoch + dt.timedelta(days=float(x)) for x in t])
