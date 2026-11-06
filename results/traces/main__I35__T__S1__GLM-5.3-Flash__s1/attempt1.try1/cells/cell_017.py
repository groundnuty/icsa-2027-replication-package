import numpy as np, datetime as dt
z=np.load('/work/extracted.npz', allow_pickle=False)
ext=z['ext']; tgt=z['tgt']
EXT=[dt.date.fromisoformat(s) for s in z['ext_dates']]
TGT=[dt.date.fromisoformat(s) for s in z['tgt_dates']]
# sea cells: finite on every target day
tgt_finite=np.isfinite(tgt)  # (92,60,60)
sea=np.all(tgt_finite, axis=0)
print('sea cells:', int(sea.sum()), 'of', tgt.size//1, 'total cells', tgt[0].size)
print('land/non-sea cells:', int((~sea).sum()))
# missing in ext per sea cell
ext_finite=np.isfinite(ext)
miss_ext = ~ext_finite
print('ext missing fraction overall:', float(miss_ext.mean()))
print('ext missing on sea cells:', float(miss_ext[:,sea].mean()))
# per sea cell count of missing ext days
mc = miss_ext[:,sea].sum(axis=0)
print('max missing days for a sea cell:', int(mc.max()), 'cells with 0 missing:', int((mc==0).sum()))
# which dates have any missing
dm = miss_ext.any(axis=(1,2))
print('ext dates with any missing:', int(dm.sum()))
# distribution of missing by year
years={}
for i,d in enumerate(EXT):
    if dm[i]:
        years[d.year]=years.get(d.year,0)+1
print('missing by year:', dict(sorted(years.items())))
# pattern of missingness per cell — random or blocks?
# find longest missing run for a sea cell
def longest_run(m):
    best=0; cur=0
    for v in m:
        cur = cur+1 if v else 0
        best=max(best,cur)
    return best
mc_all = miss_ext[:,sea]
runs=[longest_run(mc_all[:,j]) for j in range(mc_all.shape[1])]
print('longest missing run per sea cell: max', max(runs), 'mean', np.mean(runs).round(2))
print('sample missing dates:', [EXT[i].isoformat() for i in np.where(dm)[0][:15]])
# check a specific cell's missing days
j=0
midx=np.where(mc_all[:,j])[0]
print('cell 0 missing days:', [EXT[i].isoformat() for i in midx[:20]])
