import numpy as np, datetime as dt
r=np.load('/work/results.npz')
z=np.load('/work/extracted.npz', allow_pickle=False)
TGT=[dt.date.fromisoformat(s) for s in z['tgt_dates']]
mhw=r['mhw']; hot=r['hot']
# cells with mhw on t=34 (07-05)
t=34
cells=np.where(mhw[t])[0]
print('n cells mhw on', TGT[t], ':', len(cells))
# print hot & mhw pattern for a few of these cells (indices relative to sea_idx order)
for c in cells[:3]:
    print('cell', c, 'hot :', ''.join('#' if v else '.' for v in hot[:,c]))
    print('cell', c, 'mhw :', ''.join('#' if v else '.' for v in mhw[:,c]))
# and a cell with mhw on 07-07 (t=36)
t=36
cells36=np.where(mhw[t])[0]
print('n cells mhw on', TGT[t], ':', len(cells36))
for c in cells36[:3]:
    print('cell', c, 'hot :', ''.join('#' if v else '.' for v in hot[:,c]))
    print('cell', c, 'mhw :', ''.join('#' if v else '.' for v in mhw[:,c]))
# check: is mhw[t] subset of (hot[t] or gap-day)? gap days are not hot by definition...
print('mhw cells that are hot on 07-05:', int(hot[t][mhw[t]].sum()))
# For gap days: cell in mhw but not hot on 07-05 -> gap between runs
print('mhw cells NOT hot on 07-05:', int((~hot[t][mhw[t]]).sum()))
