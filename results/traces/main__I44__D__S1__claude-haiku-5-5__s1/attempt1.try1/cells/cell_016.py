import os, time
time.sleep(240)
print(len(os.listdir('/work/sub')), os.popen('tail -2 /work/fetch.log; grep -c retry /work/fetch.log; grep FAILED /work/fetch.log | head').read())