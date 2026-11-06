
import fsspec, datetime
fs = fsspec.filesystem('onedata')
base = '/icsa2027_data_20261101T090944Z/s1z'

def exists(d):
    name = 'sst_' + d.strftime('%Y%m%d') + '.nc'
    return fs.exists(base + '/' + name)

# Check edges: 1991-12-27..1991-12-31, 2003-01-01..2003-01-05, and target period
dates_to_check = []
d = datetime.date(1991,12,27)
while d <= datetime.date(1991,12,31):
    dates_to_check.append(d); d += datetime.timedelta(days=1)
d = datetime.date(2003,1,1)
while d <= datetime.date(2003,1,5):
    dates_to_check.append(d); d += datetime.timedelta(days=1)
d = datetime.date(2007,6,1)
while d <= datetime.date(2007,8,31):
    dates_to_check.append(d); d += datetime.timedelta(days=1)

missing = [d.isoformat() for d in dates_to_check if not exists(d)]
print("checked", len(dates_to_check), "dates; missing:", missing[:20], "..." if len(missing)>20 else "")
