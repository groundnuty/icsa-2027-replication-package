import os
print("cwd:", os.getcwd())
for cand in ['/tmp/workspace', os.path.expanduser('~/workspace'), os.path.expanduser('~/'), '/mnt/data', '~']:
    print(cand, "->", os.path.isdir(cand))
try:
    os.makedirs('/tmp/workspace/output', exist_ok=True); print("mkdir /tmp/workspace/output OK")
except Exception as e: print(e)
import xarray as xr
print("engines:", xr.backends.list_engines() if hasattr(xr.backends,'list_engines') else 'n/a')
