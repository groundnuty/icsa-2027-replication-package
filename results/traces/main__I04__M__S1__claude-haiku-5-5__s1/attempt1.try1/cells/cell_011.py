import subprocess, os
print(os.getcwd())
run=open("/tmp/run.py").read().replace('/tmp/output','output')
open("/tmp/run.py","w").write(run)
r=subprocess.run(["python","/tmp/run.py"],capture_output=True,text=True,cwd=os.getcwd()); print(r.stdout[-6000:], r.stderr[-1500:])
print(subprocess.run("ls -la output; cat output/report.json",shell=True,capture_output=True,text=True).stdout)