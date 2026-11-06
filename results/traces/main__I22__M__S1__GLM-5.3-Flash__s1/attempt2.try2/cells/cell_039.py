import numpy as np, datetime as dt
W = '/work/work'
hot = np.load(f'{W}/hot.npy')
sea = np.load(f'{W}/sea.npy')
tgt = np.load(f'{W}/target_data.npy').astype(np.float64)
thr = np.load(f'{W}/thr.npy')
tdates = [dt.date.fromisoformat(str(x)) for x in np.load(f'{W}/target_dates.npy')]

def doy_map(d):
    yd = d.timetuple().tm_yday
    if dt.date(d.year,12,31).timetuple().tm_yday == 366: return yd
    return yd if yd <= 59 else yd + 1
slots = np.array([doy_map(d) for d in tdates])

# run-detector unit test
def runs_of_true(m):
    out = []; n = len(m); i = 0
    while i < n:
        if m[i]:
            j = i
            while j + 1 < n and m[j+1]: j += 1
            out.append((i, j)); i = j + 1
        else: i += 1
    return out
test = np.array([1,1,1,0,1,1,1,1,1,0,0,1,1,1,1,1,0,0,0,1,1], bool)
print('runs test:', runs_of_true(test), '(expect (0,2),(4,8),(11,15),(19,20))')

# hot matrix around Aug 5-13 for a transect of sea cells
i0, i1 = 66, 75   # Aug 6..Aug 14
print('\ndates:', [str(tdates[i]) for i in range(i0, i1)])
ys, xs = np.where(sea)
sel = [(y, x) for y, x in zip(ys, xs) if x % 10 == 0][:12]
for (y, x) in sel:
    row = ''.join('1' if hot[i, y, x] else '.' for i in range(i0, i1))
    print(f'cell ({y:2d},{x:2d}): {row}')

# verify hot flags by hand for one cell, Aug 7-12
y, x = sel[1]
for i in range(i0, i1):
    sst = tgt[i, y, x]; t = thr[slots[i]-1, y, x]
    print(tdates[i], f'SST {sst:.3f} thr {t:.3f} -> hot {sst >= t} (stored flag {hot[i,y,x]})')
