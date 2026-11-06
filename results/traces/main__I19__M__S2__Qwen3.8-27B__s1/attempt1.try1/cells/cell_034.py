src = open('/work/write_out2.py').read()
src = src.replace('"lon 22.79-23.99E; 2014-06-01..2014-08-31.")}},', '"lon 22.79-23.99E; 2014-06-01..2014-08-31.")}),')
open('/work/write_out2.py','w').write(src)
import runpy
runpy.run_path('/work/write_out2.py', run_name='__main__')
