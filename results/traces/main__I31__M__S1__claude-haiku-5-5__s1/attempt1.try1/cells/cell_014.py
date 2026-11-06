import subprocess
chk=open('/tmp/analysis.py').read().split('# per-cell MHW')[0]+r'''
hot=(T>=th)&sea[None]
best=0;cnt=0
for y in range(ny):
    for x in range(nx):
        if not sea[y,x]: continue
        r=0;m=0
        for v in hot[:,y,x]:
            r=r+1 if v else 0; m=max(m,r)
        best=max(best,m); cnt+= m>=3
print('longest run',best,'cells run>=3',cnt)
print('hot per day',hot.sum(axis=(1,2))[::5])
'''
open('/tmp/chk.py','w').write(chk)
r=subprocess.run("cd /tmp && python chk.py",shell=True,capture_output=True,text=True); print(r.stdout[-3000:], r.stderr[-1000:])