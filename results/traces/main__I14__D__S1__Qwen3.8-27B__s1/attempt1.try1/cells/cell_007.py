import subprocess, os
# start big file download in background
code = '''
import fsspec, os
fs = fsspec.filesystem("onedata")
os.makedirs("/work/data", exist_ok=True)
fs.get("icsa2027_data_20261101T090944Z/s2z/sst_s2.nc", "/work/data/sst_s2.nc")
print("done")
'''
with open('/work/dl.py','w') as f:
    f.write(code)
p = subprocess.Popen(['python','/work/dl.py'], stdout=open('/work/dl.log','w'), stderr=subprocess.STDOUT, start_new_session=True)
print("started pid", p.pid)