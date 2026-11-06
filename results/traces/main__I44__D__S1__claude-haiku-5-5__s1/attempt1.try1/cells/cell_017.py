import time, os, datetime as dt
time.sleep(300)
n=len(os.listdir('/work/sub'))
exp=sum(1 for i in range((dt.date(2004,8,31)-dt.date(1991,12,27)).days+1) if (dt.date(1991,12,27)+dt.timedelta(i))<=dt.date(2003,1,5) or (dt.date(1991,12,27)+dt.timedelta(i))>=dt.date(2004,6,1))
print(n,exp, os.popen('tail -2 /work/fetch.log').read())