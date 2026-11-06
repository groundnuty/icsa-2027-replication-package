
import subprocess
r=subprocess.run(['python','/tmp/w/chk.py'],capture_output=True,text=True); print(r.stdout, r.stderr[-2000:])
