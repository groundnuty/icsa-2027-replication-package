import datetime as dt
def ex(s):
    try: return fs.exists(f'{p}/sst_{s}.nc')
    except Exception as e: return str(e)
for s in ['19920101','20021231','20030105','20190601','20190831','19911227','19840927']:print(s,ex(s))
try:
    print(len(fs.find(p)))
except Exception as e:print(e)