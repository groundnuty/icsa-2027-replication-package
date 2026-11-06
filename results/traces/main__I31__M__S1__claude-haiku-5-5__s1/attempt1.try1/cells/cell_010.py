import subprocess
r=subprocess.run("cd /tmp && python analysis.py",shell=True,capture_output=True,text=True); print(r.stdout[-4000:], r.stderr[-3000:])