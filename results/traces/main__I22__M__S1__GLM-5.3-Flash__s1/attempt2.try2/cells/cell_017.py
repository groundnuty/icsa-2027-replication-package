import datetime as dt
def doy_cal(d):
    CUM = [0,31,59,90,120,151,181,212,243,273,304,334]
    k = CUM[d.month-1] + d.day
    if d.month > 2 and d.year % 4 == 0 and (d.year % 100 != 0 or d.year % 400 == 0):
        k += 1
    return k
def doy_shift(k):
    if k <= 59: return k + 1
    if k == 60: return 0
    return k
# find slots whose window contains 1991-12-26 or 2003-01-06
for target in [dt.date(1991,12,26), dt.date(2003,1,6)]:
    hits = []
    for s in range(1, 367):
        # reconstruct slot_dates quickly
        if s <= 59: ks = [(s-1, False)]
        elif s == 60: ks = [(60, True)]
        else: ks = [(s, False), (s, True)]
        for k, leap in ks:
            for y in range(1992, 2003):
                if leap and y % 4 != 0: continue
                d0 = dt.date(y,1,1) + dt.timedelta(days=k-1)
                if any(d0 + dt.timedelta(days=off) == target for off in range(-5,6)):
                    hits.append((s, d0))
    print(target, hits[:6])
