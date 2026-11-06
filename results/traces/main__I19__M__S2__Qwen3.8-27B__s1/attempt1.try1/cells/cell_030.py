src = open('/work/verify.py').read()
src = src.replace("""def md_of_d(d):  # (month, day) fixed table
    mm = 1
    for m in range(1, 13):
        if d <= cum[m]:
            return m, d - cum[m-1]
    raise ValueError""",
"""def md_of_d(d):  # (month, day) fixed table
    mdays = [31,29,31,30,31,30,31,31,30,31,30,31]
    run = 0
    for m in range(1, 13):
        if d <= run + mdays[m-1]:
            return m, d - run
        run += mdays[m-1]
    raise ValueError""")
open('/work/verify.py','w').write(src)
import runpy
runpy.run_path('/work/verify.py', run_name='__main__')
