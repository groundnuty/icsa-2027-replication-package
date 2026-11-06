import subprocess, os
run=open("/tmp/run.py").read().replace('f"{D}/sst_20200615.nc"','"/data/icsa2027_data_20261101T090944Z/s1z/sst_20200615.nc"')
open("/tmp/run.py","w").write(run)
r=subprocess.run(["python","/tmp/run.py"],capture_output=True,text=True,cwd="/work"); print(r.stdout[-3000:], r.stderr[-800:])
print(subprocess.run("ls -la /work/output; cat /work/output/report.json; ncdump -h /work/output/mhw_mask.nc 2>/dev/null | head -30",shell=True,capture_output=True,text=True).stdout)