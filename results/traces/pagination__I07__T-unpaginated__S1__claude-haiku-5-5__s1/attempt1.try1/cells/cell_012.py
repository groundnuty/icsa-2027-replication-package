
import json, shutil, os
os.makedirs('/work/output', exist_ok=True)
shutil.copy('/tmp/w/output/mhw_mask.nc','/work/output/mhw_mask.nc')
rep=json.load(open('/tmp/w/output/report.json'))
rep['caveats']=rep['caveats']+" The single event starts on the first target day (2021-06-01) and so is truncated at the target-period start; its true onset may be earlier. Sea cells: 3292 of 3600."
json.dump(rep, open('/work/output/report.json','w'), indent=2)
print(os.listdir('/work/output'), rep['events'])
