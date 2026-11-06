import pickle, numpy as np
from datetime import date
st = pickle.load(open('/tmp/stash.pkl','rb'))
mhw = st['mhw']; dts_t = st['dts_t']; Tt = st['Tt']; LA, LO = st['LA'], st['LO']
# daily counts: cells in MHW
cnt = mhw.sum(axis=(1,2))
for i,d in enumerate(dts_t):
    if date(2003,6,25) <= d <= date(2003,8,31):
        print(d, int(cnt[i]))
