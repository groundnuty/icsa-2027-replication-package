import json
p='/work/output/report.json'
r=json.load(open(p))
r['caveats']+=" The single event begins on 2021-06-01, the first target day, so its true onset may precede the target window and is truncated by the analysis window; no days outside 2021-06-01..2021-08-31 were used for MHW detection."
json.dump(r,open(p,'w'),indent=2)
print(open(p).read()[:300])