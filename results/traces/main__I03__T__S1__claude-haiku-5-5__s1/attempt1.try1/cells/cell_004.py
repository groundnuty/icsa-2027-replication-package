import datetime as dt
dates=sorted(re.search(r'(\d{8})',n).group(1) for n in names)
print(dates[0],dates[-1], len(set(dates)))
print(any(d.startswith('1992') or d.startswith('2014') for d in dates))
print(collections.Counter(d[:4] for d in dates))