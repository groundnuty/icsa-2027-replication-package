
import json
r=json.load(open('/tmp/w/../../'+'output/report.json')) if False else None
import subprocess
code=r'''
import json
r=json.load(open("output/report.json"))
r["caveats"]+=" Event onset 2013-06-01 coincides with the target window start: MHW onset may be left-censored (true onset could be earlier, since only target-period SST was used as instructed). Per-cell MHW joining applied after the >=5-day filter."
json.dump(r,open("output/report.json","w"),indent=1)
print(r["events"], r["caveats"][:200])
'''
print(subprocess.run(['python','-c',code],capture_output=True,text=True,cwd='/tmp/w'))
