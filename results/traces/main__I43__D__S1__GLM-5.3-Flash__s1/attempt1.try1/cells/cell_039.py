import json
report = json.load(open('/work/output/report.json'))
report['caveats'] = ("No marine heatwaves were detected: every finite day-cell SST in 2017-06-01..2017-08-31 "
                     "was strictly below the cell's smoothed 90th-percentile threshold (closest approach -0.0031 K, "
                     "2017-06-24, one cell; typical deficit 2-4 K), so the per-cell MHW mask is all zeros and the "
                     "regional event list is empty. Pipeline validated: in-sample baseline (1992-2002) threshold "
                     "exceedance rate is 9.1% over sea cells, as expected for a 90th-percentile threshold. "
                     "Sea cells = 3308 of 3600 region grid cells (finite SST on every target day).")
with open('/work/output/report.json','w') as f:
    json.dump(report, f, indent=2)
print(json.dumps(report, indent=1)[:1500])
