
s2=script.replace("d2000=pd.to_datetime(dict(year=2000,month=dates.month,day=dates.day))\n    return np.asarray(d2000.dayofyear)",
 "d2000=pd.DatetimeIndex(pd.to_datetime(dict(year=2000,month=dates.month,day=dates.day)))\n    return np.asarray(d2000.dayofyear)")
open('run.py','w').write(s2)
r=subprocess.run(['python','run.py'],capture_output=True,text=True)
print(r.stdout[-6000:], r.stderr[-3000:])
