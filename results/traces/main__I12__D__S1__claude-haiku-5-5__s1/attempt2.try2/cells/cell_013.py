
s=open('/work/an.py').read()
s=s.replace("ndays=(D1-D0).days+1\ndates=[D0+dt.timedelta(days=i) for i in range(ndays)]",
"dates=[D0+dt.timedelta(days=i) for i in range((dt.date(2003,1,5)-D0).days+1)]\ndates+=[dt.date(2009,6,1)+dt.timedelta(days=i) for i in range(92)]\nndays=len(dates)")
open('/work/an.py','w').write(s)
import subprocess
r=subprocess.run(['python','/work/an.py'],capture_output=True,text=True,timeout=3000)
print(r.stdout[-6000:], r.stderr[-1500:])