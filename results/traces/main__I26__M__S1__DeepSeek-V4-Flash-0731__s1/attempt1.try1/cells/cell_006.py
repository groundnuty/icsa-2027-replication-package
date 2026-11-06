
import os
files = sorted(os.listdir('/data/icsa2027_data_20261101T090944Z/s1z'))
# Check if we have the needed baseline files
# 1991-12-27 to 2003-01-05
needed = []
import datetime
for year in [1991, 1992, 1993, 1994, 1995, 1996, 1997, 1998, 1999, 2000, 2001, 2002, 2003]:
    if year == 1991:
        start = datetime.date(1991,12,27)
        end = datetime.date(1991,12,31)
    elif year == 2003:
        start = datetime.date(2003,1,1)
        end = datetime.date(2003,1,5)
    else:
        start = datetime.date(year,1,1)
        end = datetime.date(year,12,31)
    d = start
    while d <= end:
        fname = f"sst_{d.strftime('%Y%m%d')}.nc"
        needed.append(fname)
        d += datetime.timedelta(days=1)

missing = [f for f in needed if f not in files]
print(f"Needed: {len(needed)}, missing: {len(missing)}")
print(missing[:10])
