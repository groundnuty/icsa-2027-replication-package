
import json
r=json.load(open('/data/../tmp/x.json')) if False else None
import subprocess
s=r'''
import json
rep=json.load(open('output/report.json'))
rep["caveats"]+=" The first event (onset 2013-06-01) may be truncated at the start of the target window because only target-period SST is used; the event may have started earlier."
json.dump(rep,open('output/report.json','w'),indent=1)
import xarray as xr
print(xr.open_dataset('output/mhw_mask.nc').mhw.dims)
'''
print(subprocess.run(['python','-c',s],capture_output=True,text=True,cwd='/tmp').stdout)
