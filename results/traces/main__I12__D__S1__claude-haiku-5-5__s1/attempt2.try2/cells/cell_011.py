s=open('/work/an.py').read().replace("sst_all.append(z['sst'].astype(np.float64))","sst_all.append(z['sst'].reshape(z['sst'].shape[-2],z['sst'].shape[-1]).astype(np.float64))")
open('/work/an.py','w').write(s)
import subprocess
r=subprocess.run(['python','/work/an.py'],capture_output=True,text=True,timeout=3000)
print(r.stdout[-6000:], r.stderr[-1500:])