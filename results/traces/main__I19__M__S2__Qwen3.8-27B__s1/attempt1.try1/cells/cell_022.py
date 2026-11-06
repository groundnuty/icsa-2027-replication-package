# fix: load object arrays with allow_pickle
import re
src = open('/work/pipeline2.py').read()
src = src.replace("z = np.load('/work/interim.npz')", "z = np.load('/work/interim.npz', allow_pickle=True)")
open('/work/pipeline2.py','w').write(src)
import runpy
runpy.run_path('/work/pipeline2.py', run_name='__main__')
