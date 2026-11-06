import subprocess
r=subprocess.run(['python','/tmp/m.py'],capture_output=True,text=True);print(r.stdout[-3000:],r.stderr[-2000:])