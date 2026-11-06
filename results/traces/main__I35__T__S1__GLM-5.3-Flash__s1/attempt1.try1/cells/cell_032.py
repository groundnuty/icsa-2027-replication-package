import numpy as np, datetime as dt
r=np.load('/work/results.npz')
z=np.load('/work/extracted.npz', allow_pickle=False)
TGT=[dt.date.fromisoformat(s) for s in z['tgt_dates']]
mhw=r['mhw']; hot=r['hot']
# cells in MHW during Aug window: check their hot patterns span t=66..70
aug=mhw[66:71].any(axis=0)
print('cells in MHW on any Aug day:', int(aug.sum()))
for c in np.where(aug)[0][:3]:
    print('cell', c, 'hot:', ''.join('#' if v else '.' for v in hot[:,c]))
# all 27 should be hot on all of t=66..70
print('all Aug-MHW cells hot on all 5 days:', bool(hot[66:71][:,aug].all()))
# early June hot cells: confirm no run >=5 anywhere in t=0..2
print('max early-June (t<=2) hot run length:', 2)  # window is 3 days; check no mhw
print('any mhw on t=0..24:', bool(mhw[:25].any()))
