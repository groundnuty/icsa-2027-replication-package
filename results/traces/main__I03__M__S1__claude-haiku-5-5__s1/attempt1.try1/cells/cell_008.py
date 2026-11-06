import subprocess, os
print(os.getcwd())
r=subprocess.run(f"cd {os.getcwd()} && python /tmp/an.py",shell=True,capture_output=True,text=True); print(r.stdout[-6000:], r.stderr[-3000:])