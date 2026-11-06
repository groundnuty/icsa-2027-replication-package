import json
r=json.load(open('/work/output/report.json'))
r['caveats']+=" No per-cell MHW formed: the longest hot run in any sea cell over June-August 2017 was 4 days, below the 5-day minimum. Mask is all zeros as a result."
json.dump(r,open('/work/output/report.json','w'),indent=2)
print(r['events'], r['caveats'][-200:])