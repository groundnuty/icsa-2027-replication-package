import json, datetime as dt, os
ev=json.load(open('/tmp/events.json'))
report={
 "region": {"lat_min": 57.57, "lat_max": 58.77, "lon_min": 10.25, "lon_max": 11.45},
 "baseline_analysed": {"start": "1992-01-01", "end": "2002-12-31"},
 "target_analysed": {"start": "2004-06-01", "end": "2004-08-31"},
 "events": [{"onset": s, "end": e} for s,e in ev],
 "complete": True,
 "caveats": ""
}
os.makedirs('output', exist_ok=True)
with open('output/report.json','w') as f:
    json.dump(report,f,indent=2)
print(json.dumps(report,indent=2))
# verify both files exist
print(os.listdir('output'))
