
import subprocess
s=open('/work/s1.py').read()
s=s.replace("return pd.Timestamp(2001, d.month, d.day).dayofyear","return pd.Timestamp(2000, d.month, d.day).dayofyear")
open('/work/s1.py','w').write(s)
r=subprocess.run(['python','/work/s1.py'],capture_output=True,text=True); print(r.stdout[-3000:], r.stderr[-800:])
