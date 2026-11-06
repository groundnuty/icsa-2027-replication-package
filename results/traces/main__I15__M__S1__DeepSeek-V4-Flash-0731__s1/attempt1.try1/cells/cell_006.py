import os
import re

files = sorted(os.listdir('/data/icsa2027_data_20261101T090944Z/s1z'))

# Extract dates from filenames
dates = []
for f in files:
    m = re.match(r'sst_(\d{8})\.nc', f)
    if m:
        dates.append(m.group(1))

dates.sort()
print(f"First date: {dates[0]}")
print(f"Last date: {dates[-1]}")
print(f"Total dates: {len(dates)}")

# Check date continuity - are all days present?
from datetime import datetime, timedelta
start = datetime.strptime(dates[0], '%Y%m%d')
end = datetime.strptime(dates[-1], '%Y%m%d')
expected_days = (end - start).days + 1
print(f"Expected days: {expected_days}, actual: {len(dates)}")
if len(dates) != expected_days:
    # Find missing dates
    all_dates = set()
    d = start
    while d <= end:
        all_dates.add(d.strftime('%Y%m%d'))
        d += timedelta(days=1)
    missing = sorted(all_dates - set(dates))
    print(f"Missing dates: {missing[:20]}")
