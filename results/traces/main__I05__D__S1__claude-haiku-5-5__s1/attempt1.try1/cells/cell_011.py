import subprocess
p=subprocess.run(['python','/work/mhw.py'],capture_output=True,text=True,timeout=3000)
print(p.stdout[-3000:], p.stderr[-3000:])