
import fsspec, xarray as xr, numpy as np, time, datetime as dt
from concurrent.futures import ThreadPoolExecutor
fs = fsspec.filesystem('onedata')
BASE = '/icsa2027_data_20261101T090944Z/s1z'
def read_slice_retried(datestr, tries=4):
    last=None
    for i in range(tries):
        try:
            p=f"{BASE}/sst_{datestr}.nc"; f=fs.open(p,"rb")
            try:
                ds=xr.open_dataset(f,engine="h5netcdf")
                v=ds['analysed_sst'].isel(latitude=slice(217,277),longitude=slice(421,481)).values.astype(np.float64).squeeze(axis=0)
                return v
            finally: f.close()
        except Exception as e:
            last=e; time.sleep(1.0+i)
    raise RuntimeError(f"failed {datestr}: {last}")
bdates=[dt.date(1991,12,27)+dt.timedelta(days=i) for i in range(4028)]
def do_chunk(ci):
    chunk=bdates[ci*500:min((ci+1)*500,4028)]
    t0=time.time()
    with ThreadPoolExecutor(max_workers=24) as ex:
        vals=list(ex.map(lambda d: read_slice_retried(d.strftime('%Y%m%d')), chunk))
    arr=np.stack(vals,axis=0)
    np.save(f'/tmp/mhw/baseline_part{ci}.npy', arr)
    print(f"part{ci}: {arr.shape} in {time.time()-t0:.0f}s, {chunk[0]}..{chunk[-1]}")
do_chunk(2)
