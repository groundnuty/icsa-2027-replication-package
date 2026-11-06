
import subprocess
r=subprocess.run(['python','/tmp/mhw.py'],capture_output=True,text=True)
print(r.stdout[-6000:], r.stderr[-1500:])
