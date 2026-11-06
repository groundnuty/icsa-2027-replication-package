import numpy as np, datetime as dt
r=np.load('/work/results.npz')
z=np.load('/work/extracted.npz', allow_pickle=False)
TGT=[dt.date.fromisoformat(s) for s in z['tgt_dates']]
mhw=r['mhw']; hot=r['hot']
# per-day counts of cells in MHW and hot cells
print('day counts (date, hot cells, mhw cells):')
for t in range(len(TGT)):
    if hot[t].sum()>0 or mhw[t].sum()>0:
        print(f'  {TGT[t]} hot={int(hot[t].sum()):4d} mhw={int(mhw[t].sum()):4d}')
