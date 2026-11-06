import numpy as np, datetime as dt

# verify: natural tm_yday == spec mapping
print("2015-06-01 tm_yday:", dt.date(2015,6,1).timetuple().tm_yday, "(spec: 152 for non-leap)")
print("2016-06-01 tm_yday:", dt.date(2016,6,1).timetuple().tm_yday, "(spec: 153 for leap)")
print("2015-03-01 tm_yday:", dt.date(2015,3,1).timetuple().tm_yday, "(non-leap: no day 60, so Mar1=60)")
print("2000-03-01 tm_yday:", dt.date(2000,3,1).timetuple().tm_yday, "(leap: Mar1=61)")
print("2000-02-29 tm_yday:", dt.date(2000,2,29).timetuple().tm_yday)
print("2015-08-31 tm_yday:", dt.date(2015,8,31).timetuple().tm_yday)
print("2000-12-31 tm_yday:", dt.date(2000,12,31).tm_yday, "| 2001-12-31 tm_yday:", dt.date(2001,12,31).tm_yday)
print("1992-12-31 tm_yday:", dt.date(1992,12,31).tm_yday)
