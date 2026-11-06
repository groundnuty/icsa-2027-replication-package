
import json
r=json.load(open('/data/../tmp/x.json')) if False else None
import subprocess
s=open('/tmp/mhw.py').read()
s=s.replace("Grid cropped","Event starting 2016-06-01 is truncated at the target-period start (per spec, no pre-June data used). Grid cropped")
open('/tmp/mhw.py','w').write(s)
print(subprocess.run(['python','/tmp/mhw.py'],capture_output=True,text=True,cwd='/tmp').returncode)
print(open('/tmp/output/report.json').read() if __import__('os').path.exists('/tmp/output/report.json') else 'n/a')
