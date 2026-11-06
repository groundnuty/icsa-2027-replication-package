
import subprocess
r=subprocess.run(['python','/work/s3.py'],capture_output=True,text=True); print(r.stdout[-3000:], r.stderr[-1500:])
