
chk = r'''
exec(open('/tmp/w/run.py').read().split("D=DOY[tgt_idx]")[0])
D=DOY[tgt_idx]
# baseline exceedance fraction for summer baseline days
bi=[pos[t] for t in pd.date_range('1992-06-01','2002-08-31') if t in pos]
ex=np.mean([np.mean(sub[i][sea]>=thrS[doy(T[i])][sea]) for i in bi[::7]])
print('baseline exceed frac approx', ex)
print('target mean thr-sst (cells sea):', np.nanmean(tgt[:,sea]-thrS[D][:,sea]))
print('target sst mean', np.nanmean(tgt[:,sea]), 'thr mean', np.nanmean(thrS[D][:,sea]))
print('thr sample', thrS[153][sea][:3], 'clim', climS[153][sea][:3])
# max hot run per cell
mx=0
for a in range(60):
    for b in range(60):
        if not sea[a,b]: continue
        h=(tgt[:,a,b]>=thrS[D][:,a,b]); run=0
        for x in h:
            run = run+1 if x else 0; mx=max(mx,run)
print('max hot run', mx)
'''
open('/tmp/w/chk.py','w').write(chk)
r=subprocess.run(['python','/tmp/w/chk.py'],capture_output=True,text=True); print(r.stdout, r.stderr[-2000:])
