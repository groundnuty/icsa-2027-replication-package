import os, subprocess, time
print('retry' in open('/work/fetch.py').read())
subprocess.run('pkill -f fetch.py', shell=True)
time.sleep(2)
subprocess.Popen('nohup python /work/fetch.py > /work/fetch.log 2>&1 &', shell=True)
time.sleep(90)
print(os.popen('ls /work/sub | wc -l; tail -5 /work/fetch.log').read())