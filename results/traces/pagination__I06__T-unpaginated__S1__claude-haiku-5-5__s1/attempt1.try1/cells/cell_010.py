chk = r'''
exec(open('work/mhw.py').read().split("tgt=[i")[0])
# fraction of baseline values >= smoothed threshold (should be ~10%)
bi=[i for i,d in enumerate(dates) if base_s<=d<=base_e]
bd=[doy(dates[i]) for i in bi]
site_g=[]
S=sst[bi]; ok=np.isfinite(thr_s[bd][:, :, :]).all(axis=0)
frac=np.mean(S>=thr_s[bd],axis=0)
print('baseline exceed frac median', np.nanmedian(frac))
# raw (unsmoothed) threshold exceedance
print('raw', np.nanmedian(np.mean(S>=thr[bd],axis=0)))
# target: mean SST vs clim by month
tg=[i for i,d in enumerate(dates) if d>=dt.date(2012,6,1)]
T=sst[tg]; doys=np.array([doy(dates[i]) for i in tg])
print('2012 anomaly vs clim (median over cells, per 10 days):')
an=np.nanmedian(T-clim_s[doys],axis=(1,2))
print(np.round(an,2))
print('thr minus clim median', np.nanmedian(thr_s[1:]-clim_s[1:]))
'''
exec(compile(chk,'chk','exec'))