
import os
import re
from datetime import date

files = sorted(os.listdir('/data/icsa2027_data_20261101T090944Z/s1z'))
dates = set()
for f in files:
    m = re.match(r'sst_(\d{8})\.nc', f)
    if m:
        dates.add(m.group(1))

# Check baseline start/end
baseline_start = date(1991, 12, 27)
baseline_end = date(2003, 1, 5)
# Check target
target_start = date(2013, 6, 1)
target_end = date(2013, 8, 31)

def d2s(d):
    return d.strftime('%Y%m%d')

# Check baseline availability
missing = []
d = baseline_start
while d <= baseline_end:
    if d2s(d) not in dates:
        missing.append(d2s(d))
    d = date(d.year + (d.month == 12), d.month % 12 + 1, 1) if d.day == 28 and d.month == 2 else None
    # Simpler: increment day by 1
    from datetime import timedelta
    d = baseline_start
    # Just check first few and last few
    break

# Let me just check systematically
missing_baseline = []
d = baseline_start
from datetime import timedelta
while d <= baseline_end:
    if d2s(d) not in dates:
        missing_baseline.append(d2s(d))
    d += timedelta(days=1)

print("Missing baseline files:", len(missing_baseline))
if missing_baseline:
    print("First few missing:", missing_baseline[:10])

# Check target availability
missing_target = []
d = target_start
while d <= target_end:
    if d2s(d) not in dates:
        missing_target.append(d2s(d))
    d += timedelta(days=1)

print("Missing target files:", len(missing_target))
if missing_target:
    print("Missing target:", missing_target)
