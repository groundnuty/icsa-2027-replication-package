import os
with open('/proc/meminfo') as f:
    for line in f:
        if line.startswith(('MemTotal','MemAvailable')):
            print(line.strip())
