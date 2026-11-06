import fsspec, os, time, datetime
fs = fsspec.filesystem('onedata')
base = 'icsa2027_data_20261101T090944Z/s1z'

def daterange(d0, d1):
    d = d0
    while d <= d1:
        yield d.strftime('%Y%m%d')
        d += datetime.timedelta(days=1)

base_dates = list(daterange(datetime.date(1991,12,27), datetime.date(2003,1,5)))
tgt_dates  = list(daterange(datetime.date(2021,6,1), datetime.date(2021,8,31)))
all_dates = base_dates + tgt_dates
print("baseline window days:", len(base_dates), "target days:", len(tgt_dates), "total:", len(all_dates))

# speed test: download 20 files
t0 = time.time()
os.makedirs('/work/data', exist_ok=True)
for i, dt in enumerate(tgt_dates[:20]):
    local = f'/work/data/sst_{dt}.nc'
    if not os.path.exists(local):
        fs.get(f'{base}/sst_{dt}.nc', local)
dt_ = time.time() - t0
print(f"20 files in {dt_:.1f}s -> {dt_/(20/4120)/60:.1f} min for 4120 (if same speed)")
sz = os.path.getsize(f'/work/data/sst_{tgt_dates[0]}.nc')
print("file size:", sz)
