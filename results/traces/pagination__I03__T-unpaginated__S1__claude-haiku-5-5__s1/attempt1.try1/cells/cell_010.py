
import os,subprocess
print(os.getcwd(), os.path.exists('output'), os.path.exists('/tmp/output/report.json'))
print(subprocess.run('ls -la output /tmp/output 2>&1; pwd',shell=True,capture_output=True,text=True).stdout)
