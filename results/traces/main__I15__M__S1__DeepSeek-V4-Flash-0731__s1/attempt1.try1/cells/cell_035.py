import numpy as np
from datetime import datetime, timedelta
import json

# Load data
in_mhw = np.load('/tmp/in_mhw.npy')

# Target dates
target_dates = []
d = datetime(2019, 6, 1)
while d <= datetime(2019, 8, 31):
    target_dates.append(d)
    d += timedelta(days=1)

# Active days
active = in_mhw.any(axis=0)
print("Active days pattern (A=active, .=inactive):")
pattern = ''.join(['A' if a else '.' for a in active])
print(pattern)

# Show which dates are active
for t, a in enumerate(active):
    if a:
        print(f"  {target_dates[t].strftime('%Y-%m-%d')}: active ({in_mhw[:, t].sum()} cells)")

# Read the report
with open('output/report.json') as f:
    report = json.load(f)
print(f"\nEvents in report: {report['events']}")
