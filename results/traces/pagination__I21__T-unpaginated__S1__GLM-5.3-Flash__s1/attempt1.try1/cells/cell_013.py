import fsspec, h5py, numpy as np, datetime as dt, time, pickle
from concurrent.futures import ThreadPoolExecutor
fs = fsspec.filesystem('onedata')
base = 'icsa2027_data_20261101T090944Z/s1z'
EPOCH = np.datetime64('1981-01-01', 's')

def read_region(day):
    last = None
    for attempt in range(4):
        try:
            with fs.open(f'{base}/sst_{day.strftime("%Y%m%d")}.from-base64