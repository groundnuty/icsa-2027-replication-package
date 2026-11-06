import subprocess
r=subprocess.run("cd /tmp && python dbg.py 2>/dev/null",shell=True,capture_output=True,text=True); print(r.stdout[-3000:], r.stderr[-2000:])