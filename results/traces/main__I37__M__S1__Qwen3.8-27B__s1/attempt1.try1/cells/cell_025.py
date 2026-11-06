import hashlib
for path in ('/tmp/mhw/probe.npy', '/work/probe.npy'):
    try:
        h = hashlib.sha256(open(path,'rb').read()).hexdigest()
        print(path, "sha256:", h[:16], "OK" if h.startswith('5fdef6b4600b0f6b') else "CORRUPT")
    except Exception as e:
        print(path, "ERROR", e)
