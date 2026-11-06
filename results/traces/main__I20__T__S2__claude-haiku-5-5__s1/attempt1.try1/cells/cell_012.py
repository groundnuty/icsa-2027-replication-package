
chk2 = r'''
exec(open('/tmp/w/run.py').read().split("D=DOY[tgt_idx]")[0])
D=DOY[tgt_idx]
an=tgt-climS[D]
print('target anomaly vs clim mean (K):', np.nanmean(an[:,sea]))
print('by month anomaly:', [round(float(np.nanmean(an[(T[tgt_idx].month==m)][:,sea])),2) for m in (6,7,8)])
print('thr-clim mean over target:', np.nanmean((thrS[D]-climS[D])[:,sea]))
bi=[pos[t] for t in pd.date_range('1992-06-01','2002-08-31') if t in pos]
ba=np.mean([np.nanmean(sub[i][sea]-climS[doy(T[i])][sea]) for i in bi])
print('baseline mean anomaly (should be ~0):', ba)
'''
open('/tmp/w/chk2.py','w').write(chk2)
r=subprocess.run(['python','/tmp/w/chk2.py'],capture_output=True,text=True); print(r.stdout, r.stderr[-2000:])
