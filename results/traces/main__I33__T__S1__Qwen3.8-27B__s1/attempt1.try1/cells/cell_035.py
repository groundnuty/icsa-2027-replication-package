
import numpy as np, pickle
M = np.load('/work/work/M.npy')
with open('/work/work/dates.pkl','rb') as f: D = pickle.load(f)
target_dates, sea = D['target'], D['sea']
print("day: n_cells_in_MHW (event window)")
for k, t in enumerate(target_dates):
    if '2014-07-15' <= t.isoformat() <= '2014-08-25':
        print("  ", t.isoformat(), int(M[k].sum()))
