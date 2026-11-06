
import pandas as pd, json, os, warnings
warnings.filterwarnings('ignore')
T=base.time.values.astype('datetime64[D]')
def doy(d):
    d=pd.Timestamp(d)
    # map by month/day using leap-year calendar
    ref=pd.Timestamp(2000,d.month,d.day)  # 2000 is leap
    n=ref.dayofyear
    if d.month==2 and d.day==29: return 60
    if n>=61 and not (d.month==2 and d.day==29): 
        return n if True else n
    return n
# ref doy in leap year: Mar1=61 ; for non-leap years shift >=61 back by one to match? spec: 1 Mar =61 in both.
def doy_map(d):
    d=pd.Timestamp(d)
    if d.month==2 and d.day==29: return 60
    n=pd.Timestamp(2001,d.month,d.day).dayofyear  # non-leap
    if d.month>2 or (d.month==2): n=n+ (1 if (d.month>2 or (d.month==2 and d.day>=29)) else 0)
    return n
# simpler: explicit
def doy2(d):
    d=pd.Timestamp(d)
    if d.month==2 and d.day==29: return 60
    n=pd.Timestamp(2001,d.month,d.day).dayofyear
    if d.month>2 and pd.Timestamp(d.year,1,1).is_leap_year: n+=1
    if d.month>2 and not pd.Timestamp(d.year,1,1).is_leap_year: n+=0
    return n
# verify: non-leap: Mar1 ->61 requires +1 in non-leap year ( 2001 Mar1 doy=60 ); leap year Mar1 doy=61 already
def doy3(d):
    d=pd.Timestamp(d)
    if d.month==2 and d.day==29: return 60
    n=pd.Timestamp(2001,d.month,d.day).dayofyear  # ref non-leap
    if d.month>2: n+=1   # after Feb: shift so Mar1=61 (non-leap 2001 Mar1=60)
    return n
print(doy3('2001-03-01'),doy3('2001-12-31'),doy3('2000-03-01'),doy3('2000-12-31'),doy3('2001-02-28'),doy3('2000-02-29'))
