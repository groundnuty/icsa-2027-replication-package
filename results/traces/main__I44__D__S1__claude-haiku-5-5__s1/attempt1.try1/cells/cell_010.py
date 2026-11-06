import os, subprocess, time
subprocess.Popen('nohup python /work/fetch.py > /work/fetch.log 2>&1 &', shell=True)
time.sleep(60)
print(os.popen('ls /work/sub | wc -l; cat /work/fetch.log; df -h /work|tail -1').read())