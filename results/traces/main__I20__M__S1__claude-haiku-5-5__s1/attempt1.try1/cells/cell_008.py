code=open("/tmp/mhw.py").read()
code=code.replace('''    d=t.dayofyear
    if t.is_leap_year and t > pd.Timestamp(t.year,2,29): d-=1
    return d''','''    d=t.dayofyear
    if (not t.is_leap_year) and t.month>=3: d+=1
    return d''')
open("/tmp/mhw.py","w").write(code)
import subprocess
r=subprocess.run("cd /tmp && python mhw.py",shell=True,capture_output=True,text=True); print(r.stdout, r.stderr[-3000:])