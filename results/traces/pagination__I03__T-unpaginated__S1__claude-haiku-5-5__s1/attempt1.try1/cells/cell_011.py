
import subprocess, os
r=subprocess.run(['python','/tmp/run.py'],capture_output=True,text=True,cwd='/work')
print(r.stdout, r.stderr[-1000:])
print(subprocess.run('ls -la /work/output; cat /work/output/report.json',shell=True,capture_output=True,text=True).stdout)
