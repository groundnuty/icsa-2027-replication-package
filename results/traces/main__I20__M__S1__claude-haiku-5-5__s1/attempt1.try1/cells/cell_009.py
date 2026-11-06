dbg=r'''
import numpy as np
exec(open("/tmp/mhw.py").read().split("mhw=np.zeros")[0])
print("hot per day", hot.sum(axis=(1,2))[:95])
mx=[]
for y in range(60):
  for x in range(60):
    if not sea[y,x]: continue
    h=hot[:,y,x]; run=0; best=0
    for v in h:
        run=run+1 if v else 0; best=max(best,run)
    mx.append(best)
print("max runs hist", np.bincount(mx))
print("T sample", T[150,30,30], clim[1:][150,30,30] if False else C[150,30,30], S[:3,30,30])
'''
open("/tmp/dbg.py","w").write(dbg)
r=subprocess.run("cd /tmp && python dbg.py 2>/dev/null",shell=True,capture_output=True,text=True); print(r.stdout[-3000:], r.stderr[-2000:])