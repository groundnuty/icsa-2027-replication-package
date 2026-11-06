import numpy as np, time
t0=time.time()
base = np.load('/tmp/sst_base.npy')
bdates = np.load('/tmp/bdates.npy')
B = bdates.astype('int64')
N = len(B)
bstart = 5; bend = 4022
is_baseline = np.zeros(N, bool); is_baseline[bstart:bend+1]=True

# (month, day) based day-of-year, leap-year calendar: Jan1=1, Feb28=59, Feb29=60, Mar1=61, Dec31=366
ml = np.array([31,29,31,30,31,30,31,31,30,31,30,31])
pref = np.concatenate([[0], np.cumsum(ml)])
bm = np.array([int(np.datetime_as_string(d, unit='M').split('-')[1]) for d in bdates])
bd = np.array([int(np.datetime_as_string(d, unit='D')[8:10]) for d in bdates])
doy = pref[bm-1] + bd
np.save('/tmp/base_doy.npy', doy)
# verify
for d_ in [np.datetime64('1992-02-28'), np.datetime64('1992-02-29'), np.datetime64('1992-03-01'),
           np.datetime64('2001-03-01'), np.datetime64('2001-12-31'), np.datetime64('1991-12-27'), np.datetime64('2003-01-05')]:
    i = int(np.searchsorted(B, d_.astype('int64')))
    print(d_, '-> doy', doy[i])

pools = {}
for d in range(1, 367):
    pos = np.nonzero(is_baseline & (doy==d))[0]
    if pos.size == 0:
        pools[d] = np.array([], int); continue
    lo = np.clip(pos-5, 0, N-1); hi = np.clip(pos+5, 0, N-1)
    idx = np.unique(np.concatenate([np.arange(l, h+1) for l,h in zip(lo,hi)]))
    pools[d] = idx
pools_arr = np.array([pools[d] for d in range(1,367)], dtype=object)
np.save('/tmp/pools.npy', pools_arr, allow_pickle=True)
sizes = np.array([pools[d].size for d in range(1,367)])
print('pool sizes: min', sizes.min(), 'max', sizes.max())
print('d60 size', pools[60].size, 'dates:', [str(x) for x in bdates[pools[60][::15]]])
print('d366 size', pools[366].size, 'last dates:', [str(x) for x in bdates[pools[366][-6:]]])
print('d61 size', pools[61].size, 'first:', [str(x) for x in bdates[pools[61][:6]]])
# check every non-60 pool: each should be union of 11 windows (11 baseline dates for 366, 11 others)
exp = {60:33, 366:121}
bad = [d for d in range(1,367) if pools[d].size not in (exp.get(d,121),) and d not in (60,366)]
print('pools with unexpected size:', bad)
print('elapsed %.1fs' % (time.time()-t0))
