import os, subprocess, time
print(subprocess.run("ps aux | grep fetch.py | grep -v grep", shell=True, capture_output=True, text=True).stdout)
for line in subprocess.run("ps aux | grep fetch.py | grep -v grep", shell=True, capture_output=True, text=True).stdout.splitlines():
    os.kill(int(line.split()[1]), 9)
time.sleep(2)
for f in os.listdir('/work/raw'): os.remove('/work/raw/'+f)
print(len(os.listdir('/work/sub')))