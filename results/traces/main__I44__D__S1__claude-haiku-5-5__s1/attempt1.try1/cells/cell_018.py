import time, os
time.sleep(200)
print(len(os.listdir('/work/sub')), os.popen('tail -2 /work/fetch.log; grep -c retry /work/fetch.log').read())