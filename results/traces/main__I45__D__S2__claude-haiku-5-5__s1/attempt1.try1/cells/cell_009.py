
import subprocess
r=subprocess.run(['python','/work/main.py'],capture_output=True,text=True); print(r.stdout[-6000:], r.stderr[-3000:])
