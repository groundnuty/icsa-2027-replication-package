import os
for p in ['/sys/fs/cgroup/memory.max','/sys/fs/cgroup/memory.current','/sys/fs/cgroup/memory/memory.limit_in_bytes','/sys/fs/cgroup/memory/memory.usage_in_bytes']:
    try:
        print(p, open(p).read().strip())
    except Exception as e:
        print(p, "ERR", e)
# also check page cache of the nc file via /proc/self
print(os.popen("ls -la /work/data/").read())