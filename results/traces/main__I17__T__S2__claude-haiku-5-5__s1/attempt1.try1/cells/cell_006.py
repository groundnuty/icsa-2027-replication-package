
s=open('/tmp/mhw.py').read()
old=s[s.index('def doy_of(d):'):s.index('bdoy=doy_of(bt)')]
new='''def doy_of(d):
    d=pd.DatetimeIndex(d)
    # leap-year (2000) day-of-year: 28 Feb=59, 29 Feb=60, 1 Mar=61
    x=np.array([pd.Timestamp(2000,m,dd).dayofyear for m,dd in zip(d.month,d.day)])
    return x
'''
s=s.replace(old,new)
s=s.replace('print("check doy:", doy_of(pd.DatetimeIndex([\'2004-02-28\',\'2004-02-29\',\'2004-03-01\',\'2004-12-31\'])))',
            'print("check doy:", doy_of(pd.DatetimeIndex([\'2004-02-28\',\'2004-02-29\',\'2004-03-01\',\'2004-12-31\'])))')
open('/tmp/mhw.py','w').write(s)
r=subprocess.run(['python','/tmp/mhw.py'],capture_output=True,text=True)
print(r.stdout[-6000:], r.stderr[-1500:])
