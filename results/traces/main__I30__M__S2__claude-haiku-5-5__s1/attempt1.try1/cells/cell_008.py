
import os, subprocess
print(os.getcwd())
r=subprocess.run(['python','/tmp/mhw.py'],capture_output=True,text=True)
print(r.stdout[-600:], r.stderr[-1000:])
print(os.path.abspath('output'), os.listdir('output'))
print(open('output/report.json').read())
