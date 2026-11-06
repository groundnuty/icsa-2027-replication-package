from datetime import date
# verify correct month/day-based doy
cum = [0,31,60,91,121,152,182,213,244,274,305,335]  # leap-year calendar: Feb=29
def doy(d):
    return cum[d.month-1] + d.day
checks = [(date(2021,1,1),1),(date(2021,2,28),59),(date(2020,2,29),60),(date(2021,3,1),61),
          (date(2021,12,31),366),(date(2020,12,31),366),(date(2021,7,1),182)]
print([(d, doy(d), exp, doy(d)==exp) for d,exp in checks])
# and the broken one for reference:
print("broken:", (date(2021,3,1)-date(2021,1,1)).days+1, (date(2021,12,31)-date(2021,1,1)).days+1)
