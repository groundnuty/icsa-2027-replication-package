
import os, shutil, subprocess
cwd=os.getcwd(); print(cwd)
if os.path.abspath(cwd)!='/tmp':
    os.makedirs(os.path.join(cwd,'output'),exist_ok=True)
    for f in ['mhw_mask.nc','report.json']:
        shutil.copy(f'/tmp/output/{f}', os.path.join(cwd,'output',f))
print(os.listdir(os.path.join(cwd,'output')))
