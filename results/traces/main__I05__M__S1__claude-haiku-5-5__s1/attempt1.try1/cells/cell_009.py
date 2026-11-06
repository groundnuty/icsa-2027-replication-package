import subprocess
code=open('/tmp/mhw.py').read()
code=code.replace("thr_s=smooth(thr[1:].reshape(366,nlat,nlon) if False else thr) if False else None\n","")
code=code.replace("/tmp/output","/work/output")
open('/tmp/mhw.py','w').write(code)
r=subprocess.run("cd /work && python /tmp/mhw.py", shell=True, capture_output=True, text=True); print(r.stdout, r.stderr[-3000:])