
diag2 = r'''
import numpy as np
exec(open('/tmp/run.py').read().split("# per-cell MHW")[0])
for Y in range(1991,2005):
    m=np.array([d.year==Y for d in dates])
    x=cube[m][:,sea]
    if x.size: print(Y, np.round(np.nanmin(x),2), np.round(np.nanmax(x),2), np.round(np.nanmean(x),2), m.sum())
doys=np.array([doy(d) for d in tgt])
hot=T>=thr[doys-1]
# longest hot run per sea cell
mx=[]
for a,b in zip(*np.where(sea)):
    h=hot[:,a,b]; best=cur=0
    for v in h:
        cur=cur+1 if v else 0; best=max(best,cur)
    mx.append(best)
print('max run hist', np.bincount(mx))
print('hot per day', hot[:,sea].sum(axis=1))
'''
open('/tmp/diag2.py','w').write(diag2)
r=subprocess.run(['python','/tmp/diag2.py'],capture_output=True,text=True)
print(r.stdout[-5000:], r.stderr[-3000:])
