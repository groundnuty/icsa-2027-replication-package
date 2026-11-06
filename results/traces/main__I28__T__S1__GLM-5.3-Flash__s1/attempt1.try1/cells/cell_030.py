import numpy as np
from datetime import date, timedelta
st3 = np.load('/tmp/stage3b.npz')
target_dates = []
d = date(2013,6,1)
while d <= date(2013,8,31):
    target_dates.append(d); d += timedelta(days=1)
def evs(M):
    M3 = M.reshape(M.shape[0], 60, 60)
    act = M3.any(axis=(1,2))
    out=[]; i=0
    while i<len(act):
        if act[i]:
            j=i
            while j+1<len(act) and act[j+1]: j+=1
            out.append((target_dates[i], target_dates[j])); i=j+1
        else: i+=1
    return out
for mode in ('A','C'):
    M = st3[mode]
    print(mode, [(str(a), str(b)) for a,b in evs(M)])
