
import subprocess
r=subprocess.run(['python','/tmp/diag.py'],capture_output=True,text=True)
print(r.stdout[-5000:], r.stderr[-3000:])
