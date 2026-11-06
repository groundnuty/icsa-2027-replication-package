path = '/work/verify2.py'
src = open(path).read()
old = """events2 = []
for k in range(1, n2+1):
    idx = np.where(lab2 == k)[0]
    events2.append((str(idx[0]), str(idx[-1])))
tdays = [str(x) for x in (np.datetime64('2021-06-01') + np.arange(92, dtype='int64')*np.timedelta64(1,'D'))]
events2 = [(tdays[s], tdays[e]) for s, e in events2]"""
new = """raw = []
for k in range(1, n2+1):
    idx = np.where(lab2 == k)[0]
    raw.append((int(idx[0]), int(idx[-1])))
tdays = [str(x) for x in (np.datetime64('2021-06-01') + np.arange(92, dtype='int64')*np.timedelta64(1,'D'))]
events2 = [(tdays[s], tdays[e]) for s, e in raw]"""
assert old in src
src = src.replace(old, new)
open(path, 'w').write(src)
exec(src)
