import h5py, numpy as np, time, os

path = "/data/icsa2027_data_20261101T090944Z/s2z/sst_s2.nc"
f = h5py.File(path, "r")
d = f["analysed_sst"]
# coordinate slices
lat = f["latitude"][:].astype(np.float64)
lon = f["longitude"][:].astype(np.float64)
lati = np.where((lat >= 63.31) & (lat <= 64.51))[0]
loni = np.where((lon >= 21.31) & (lon <= 22.51))[0]
la0, la1 = int(lati[0]), int(lati[-1])
lo0, lo1 = int(loni[0]), int(loni[-1])
nt_lat, nt_lon = la1 - la0 + 1, lo1 - lo0 + 1

tvals = f["time"][:]  # ints
# decode time units
import re
units = f["time"].attrs["units"]
if isinstance(units, bytes): units = units.decode()
print("time units:", units)
m = re.match(r"(\w+) since ([\d\-:T ]+)", units)
unitw, origin = m.group(1), m.group(2).strip()
from datetime import datetime, timedelta
base_dt = datetime.fromisoformat(origin)
secmap = {"seconds":1, "minutes":60, "hours":3600, "days":86400}
dates_all = np.array([base_dt + timedelta(seconds=int(t)*secmap[unitw]) for t in tvals[:]])
print("date range:", dates_all[0].date(), dates_all[-1].date(), "n =", len(dates_all))

def dstr(dt): return dt.strftime("%Y-%m-%d")
from datetime import date
want = [dstr(dt) for dt in dates_all]
idx = {s:i for i,s in enumerate(want)}

# day lists
baseline = [ (date(1991,12,27)+timedelta(days=i)).strftime("%Y-%m-%d") for i in range((date(2003,1,5)-date(1991,12,27)).days+1) ]
target   = [ (date(2004,6,1)+timedelta(days=i)).strftime("%Y-%m-%d") for i in range((date(2004,8,31)-date(2004,6,1)).days+1) ]
alldays = baseline + target
print("n baseline days:", len(baseline), baseline[0], baseline[-1])
print("n target days:", len(target), target[0], target[-1])
missing = [s for s in alldays if s not in idx]
print("missing dates in dataset:", missing)

# read
t0=time.time()
block = np.empty((len(alldays), nt_lat, nt_lon), dtype=np.float32)
for i,s in enumerate(alldays):
    j = idx[s]
    block[i] = d[j, la0:la1+1, lo0:lo1+1]
t1=time.time()
print("read", t1-t0, "s; block", block.shape, block.dtype)
np.save("/tmp/sst_block.npy", block)
with open("/tmp/alldays.txt","w") as fh: fh.write("\n".join(alldays))
with open("/tmp/slices.txt","w") as fh: fh.write(f"{la0} {la1} {lo0} {lo1}\n")
# quick stats
fin = np.isfinite(block)
print("finite frac overall:", fin.mean())
fin_t = fin[len(baseline):]
sea_cells = fin_t.all(axis=0)
print("sea cells in region:", int(sea_cells.sum()), "of", sea_cells.size)
np.save("/tmp/sea_cells.npy", sea_cells)
f.close()
