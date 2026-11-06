
import json
from datetime import date, timedelta

# Regional events
per_cell_mhw = __import__('numpy').load('/tmp/per_cell_mhw.npy')

target_dates = []
d = date(2009, 6, 1)
while d <= date(2009, 8, 31):
    target_dates.append(d)
    d += timedelta(days=1)

active = per_cell_mhw.any(axis=(1, 2))
events = []
t = 0
while t < len(active):
    if active[t]:
        start = t
        while t < len(active) and active[t]:
            t += 1
        events.append({
            'onset': target_dates[start].strftime('%Y-%m-%d'),
            'end': target_dates[t-1].strftime('%Y-%m-%d')
        })
    else:
        t += 1

report = {
    'region': {
        'lat_min': 56.09,
        'lat_max': 57.29,
        'lon_min': 10.55,
        'lon_max': 11.75
    },
    'baseline_analysed': {
        'start': '1991-12-27',
        'end': '2003-01-05'
    },
    'target_analysed': {
        'start': '2009-06-01',
        'end': '2009-08-31'
    },
    'events': events,
    'complete': True,
    'caveats': ''
}

with open('output/report.json', 'w') as f:
    json.dump(report, f, indent=2)

print(json.dumps(report, indent=2))
