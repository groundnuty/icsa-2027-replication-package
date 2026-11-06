
import json

report = {
    'region': {
        'lat_min': 56.13,
        'lat_max': 57.33,
        'lon_min': 17.71,
        'lon_max': 18.91
    },
    'baseline_analysed': {
        'start': '1991-12-27',
        'end': '2003-01-05'
    },
    'target_analysed': {
        'start': '2019-06-01',
        'end': '2019-08-31'
    },
    'events': [
        {'onset': '2019-06-16', 'end': '2019-07-02'}
    ],
    'complete': True,
    'caveats': ''
}

with open('output/report.json', 'w') as f:
    json.dump(report, f, indent=2)

print(json.dumps(report, indent=2))
