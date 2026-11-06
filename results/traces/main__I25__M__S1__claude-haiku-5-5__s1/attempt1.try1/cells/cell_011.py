import subprocess
w=open('/tmp/write.py').read().replace("os.makedirs('/data_out_placeholder',exist_ok=True) if False else None\n","")
open('/tmp/write.py','w').write(w)
r=subprocess.run(['python','/tmp/write.py'],capture_output=True,text=True,cwd='/work'); print(r.stdout, r.stderr[-2000:])
print(subprocess.run('ls -la /work/output; python -c "import xarray as xr;d=xr.open_dataset(\'/work/output/mhw_mask.nc\');print(d);print(int(d.mhw.sum()))"',shell=True,capture_output=True,text=True).stdout)