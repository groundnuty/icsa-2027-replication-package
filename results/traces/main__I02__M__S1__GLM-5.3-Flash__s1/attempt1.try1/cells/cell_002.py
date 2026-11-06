import os
d='/data/icsa2027_data_20261101T090944Z/s1z'
files=sorted(os.listdir(d))
print(len(files), files[0], files[-1])
# check for gaps in the daily sequence
import datetime as dt
names=[f[4:12] for f in files]
dates=[dt.datetime.strptime(n,'%Y%m%d').date() for n in names]
gaps=[]
for a,b in zip(dates, dates[1:]):
    if (b-a).days!=1:
        gaps.append((str(a),str(b),(b-a).days))
print("gaps:", gaps[:20], "count:", len(gaps))
print("first:", dates[0], "last:", dates[-1])
