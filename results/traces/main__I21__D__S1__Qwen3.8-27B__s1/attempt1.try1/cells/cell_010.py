import fsspec, os, time, datetime
fs = fsspec.filesystem('onedata')
base = 'icsa2027_data_20261101T090944Z/s1z'

def daterange(d0, d1):
    d = d0
    while d <= d1:
        yield d.strftime('%Y%m%d')
        d += datetime.timedelta(days=1)

all_dates = list(daterange(datetime.date(1991,12,27), datetime.date(2003,1,5))) + \
            list(daterange(datetime.date(2021,6,1), datetime.date(2021,8,31)))
print("total:", len(all_dates))
os.makedirs('/work/data', exist_ok=True)
missing = []
t0 = time.time()
for i, dt in enumerate(all_dates):
    local = f'/work/data/sst_{dt}.nc'
    if not os.path.exists(local):
        try:
            fs.get(f'{base}/sst_{dt}.nc', local)
        except Exception as e:
            missing.append((dt, str(e)[:80]))
    if (i+1) % 500 == 0:
        print(f"{i+1}/{len(all_dates)} done, {time.time()-t0:.0f}s, missing so far: {len(missing)}")
print("done in", round(time.time()-t0,1), "s; missing:", missing[:20], "count:", len(missing))
