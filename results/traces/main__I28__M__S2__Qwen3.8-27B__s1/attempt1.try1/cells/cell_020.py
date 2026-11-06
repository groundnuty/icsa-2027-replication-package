p = "/usr/local/lib/python3.12/site-packages/numpy/lib/_nanfunctions_impl.py"
src = open(p).read().splitlines()
for i, l in enumerate(src):
    if "def nanpercentile" in l:
        print("\n".join(src[i:i+80]))
        break
