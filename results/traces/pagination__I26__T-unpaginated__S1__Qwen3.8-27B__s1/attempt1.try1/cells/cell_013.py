s = open('/work/mhw_analyse.py').read()
old = """cum = [31, 60, 91, 121, 152, 182, 213, 244, 274, 305, 335, 366]
def doy_of(d): return cum[d.month-1] + d.day
def md_of(doy):  # inverse: doy -> (month, day)
    for m in range(1, 13):
        lo = cum[m-1] + 1
        hi = cum[m]
        if lo <= doy <= hi: return (m, doy - cum[m-1])
    raise ValueError(doy)"""
new = """eom = [0, 31, 60, 91, 121, 152, 182, 213, 244, 274, 305, 335, 366]  # eom[m-1] = end of previous month (leap calendar)
def doy_of(d): return eom[d.month-1] + d.day
def md_of(doy):  # inverse: doy -> (month, day)
    for m in range(1, 13):
        if eom[m-1] < doy <= eom[m]: return (m, doy - eom[m-1])
    raise ValueError(doy)
# sanity
assert doy_of(date(1992,1,1)) == 1 and doy_of(date(1992,2,28)) == 59 and doy_of(date(1992,2,29)) == 60
assert doy_of(date(1992,3,1)) == 61 and doy_of(date(1992,12,31)) == 366 and doy_of(date(1993,1,1)) == 1
assert md_of(1) == (1,1) and md_of(60) == (2,29) and md_of(61) == (3,1) and md_of(366) == (12,31)"""
assert old in s
s = s.replace(old, new)
open('/work/mhw_analyse.py', 'w').write(s)
print("patched")
