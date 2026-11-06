
s2 = open('/tmp/run.py').read().split("active=mhw")[0] + r'''
mx=0
for y in range(60):
    for x in range(60):
        if not sea[y,x]: continue
        r=runs(hot[:,y,x])
        if r: mx=max(mx,max(b-a+1 for a,b in r))
print('max hot run', mx)
print('hot cells per day', hot.sum(axis=(1,2)).tolist())
print('regional mean SST first/last days', np.nanmean(T[:,sea],axis=1)[[0,30,60,91]], 'mean thr', np.nanmean(TH[:,sea],axis=1)[[0,30,60,91]])
'''
open('/tmp/chk.py','w').write(s2)
import subprocess
r=subprocess.run(['python','/tmp/chk.py'],capture_output=True,text=True,cwd='/tmp'); print(r.stdout, r.stderr[-2000:])