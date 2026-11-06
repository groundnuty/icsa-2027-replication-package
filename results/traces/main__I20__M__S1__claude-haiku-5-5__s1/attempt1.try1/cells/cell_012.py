import subprocess,os
print(os.getcwd())
open("/tmp/write.py","w").write(open("/tmp/write.py").read())
r=subprocess.run("cd /tmp && python write.py && ls -la /tmp/output && cat /tmp/output/report.json | head -30",shell=True,capture_output=True,text=True); print(r.stdout, r.stderr[-2000:])