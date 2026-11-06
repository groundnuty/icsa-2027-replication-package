def doy(d):
    return (datetime.date(2000,d.month,d.day)-datetime.date(2000,1,1)).days+1
assert doy(datetime.date(1992,2,28))==59 and doy(datetime.date(1993,3,1))==61 and doy(datetime.date(1993,12,31))==366 and doy(datetime.date(1993,2,28))==59 and doy(datetime.date(1993,2,28))==59
assert doy(datetime.date(1996,2,29))==60 and doy(datetime.date(1993,12,30))==365
base_start=datetime.date(1992,1,1); base_end=datetime.date(2002,12,31)
idx_of={d:i for i,d in enumerate(dates)}
pools={k:set() for k in range(1,367) if k!=60}
for b in dates:
    if not (base_start<=b<=base_end): continue
    k=doy(b)
    if k==60: continue
    for off in range(-5,6):
        pools[k].add(b+datetime.timedelta(off))
print([len(pools[k]) for k in (1,59,61,366,365)], [len([d for d in pools[k] if d in idx_of]) for k in (1,59,61,366,365)])
print('missing pool dates', [str(d) for d in pools[1] if d not in idx_of][:5])