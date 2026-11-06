import os
for f in ['output/mhw_mask.nc', 'output/report.json']:
    print(f, os.path.getsize(f), 'bytes')
import json
r = json.load(open('output/report.json'))
print('report keys:', sorted(r.keys()), '| complete:', r['complete'], '| n events:', len(r['events']))
