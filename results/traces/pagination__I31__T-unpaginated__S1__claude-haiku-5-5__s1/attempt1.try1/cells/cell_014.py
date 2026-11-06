
import subprocess
code2 = open('work/compute.py').read().split("active=mhw.any")[0] + r'''
print('T range', np.nanmin(T[:,sea]), np.nanmax(T[:,sea]))
print('thr summer sample', thr_s[153][sea][:5], thr_s[230][sea][:5])
print('thr-clim mean summer', np.nanmean(thr_s[153:245][:,sea]-clim_s[153:245][:,sea]))
mx=0
for i in range(ny):
    for j in range(nx):
        if not sea[i,j]: continue
        run=0
        for v in hot[:,i,j]:
            run=run+1 if v else 0; mx=max(mx,run)
print('max hot run', mx)
print('max daily hot cells', hot.sum(axis=(1,2)).max(), 'days with any hot', hot.any(axis=(1,2)).sum())
'''
open('work/check.py','w').write(code2)
r=subprocess.run(['python','work/check.py'],capture_output=True,text=True); print(r.stdout[-4000:], r.stderr[-1500:])
