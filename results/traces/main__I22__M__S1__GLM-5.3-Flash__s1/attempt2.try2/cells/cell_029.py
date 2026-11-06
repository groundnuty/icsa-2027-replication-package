import os, time, json, datetime as dt
import numpy as np
import h5py

d = '/data/icsa2027_data_20261101T090944Z/s1z'
W = '/work/work'
os.makedirs(W, exist_ok=True)

ILAT0, ILAT1 = 196, 256   # python slice: 196:256
ILON0, ILON1 = 485, 545

EPOCH = dt.date(1981, 1, 1)

def expected_seconds(date):
    return (date - EPOCH).days * 86400

# date lists
baseline_dates = []
cur = dt.date(1991, 12, 27)
while cur <= dt.date(2003, 1, 5):
    baseline_dates.append(cur); cur += dt.timedelta(days=1)
target_dates = []
cur = dt.date(2004, 6, 1)
while cur <= dt.date(2004, 8, 31):
    target_dates.append(cur); cur += dt.timedelta(days=1)
print('baseline days:', len(baseline_dates), '| target days:', len(target_dates))

data = np.full((len(baseline_dates), 60, 60), np.nan, dtype=np.float32)
tgt  = np.full((len(target_dates), 60, 60), np.nan, dtype=np.float32)

t0 = time.time()
nbad = 0
for i, date in enumerate(baseline_dates):
    p = f'{d}/sst_{date.strftime("%Y%m%d")}.nc'
    with h5py.File(p, 'r') as f:
        tv = f['time'][0]
        if tv != expected_seconds(date):
            print('TIME MISMATCH', date, tv, expected_seconds(date)); nbad += 1
        data[i] = f['analysed_sst'][0, ILAT0:ILAT1, ILON0:ILON1]
    if (i + 1) % 500 == 0:
        np.save(f'{W}/baseline_data.npy', data)
        print(f'baseline {i+1}/{len(baseline_dates)}  ({time.time()-t0:.0f} s)', flush=True)
np.save(f'{W}/baseline_data.npy', data)
print('baseline reads done:', f'{time.time()-t0:.0f} s, time mismatches: {nbad}', flush=True)

t0 = time.time()
for i, date in enumerate(target_dates):
    p = f'{d}/sst_{date.strftime("%Y%m%d")}.nc'
    with h5py.File(p, 'r') as f:
        tv = f['time'][0]
        if tv != expected_seconds(date):
            print('TIME MISMATCH', date, tv, expected_seconds(date)); nbad += 1
        tgt[i] = f['analysed_sst'][0, ILAT0:ILAT1, ILON0:ILON1]
np.save(f'{W}/target_data.npy', tgt)
print('target reads done:', f'{time.time()-t0:.0f} s, cumulative time mismatches: {nbad}')

np.save(f'{W}/baseline_dates.npy', np.array([x.isoformat() for x in baseline_dates]))
np.save(f'{W}/target_dates.npy', np.array([x.isoformat() for x in target_dates]))
print('finite fraction baseline:', np.isfinite(data).mean(), '| target:', np.isfinite(tgt).mean())
