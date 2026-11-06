
s=open('/work/an.py').read()
s=s.replace("D0=dt.date(1991,12,27); D1=dt.date(2003,1,5)","D0=dt.date(1991,12,27); D1=dt.date(2009,8,31)")
s=s.replace("print('shape',S.shape","nanday=np.isnan(S).reshape(S.shape[0],-1).sum(1)\nprint('nan per day sample', [(dates[i].isoformat(),int(nanday[i])) for i in range(0,len(dates),400)], 'cells nan ever', int(np.isnan(S).any(0).sum()), 'cells nan in target', int(np.isnan(S[[idx for idx in range(len(dates)) if dates[idx]>=dt.date(2009,6,1)]]).any(0).sum()))\nprint('shape',S.shape")
s=s.replace("print('sea cells', sea.sum(), 'of', ncell)","print('sea cells', sea.sum(), 'of', ncell)\nprint('target dates', nt if False else len(tdates))")
s=s.replace("ndays=(D1-D0).days+1","ndays=(D1-D0).days+1")
open('/work/an.py','w').write(s)
import subprocess
r=subprocess.run(['python','/work/an.py'],capture_output=True,text=True,timeout=3000)
print(r.stdout[-6000:], r.stderr[-1500:])