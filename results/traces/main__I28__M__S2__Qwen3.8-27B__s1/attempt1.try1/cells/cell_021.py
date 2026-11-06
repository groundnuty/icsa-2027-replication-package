p = "/usr/local/lib/python3.12/site-packages/numpy/lib/_nanfunctions_impl.py"
src = open(p).read().splitlines()
for i, l in enumerate(src):
    if "def nanpercentile" in l:
        # find end of docstring and print body
        j = i
        while '"""' not in src[j] or j == i:
            j += 1
        # count to closing triple quote
        cnt = src[j].count('"""')
        if cnt < 2:
            j += 1
        while True:
            if src[j].count('"""') >= 1:
                break
            j += 1
        print("\n".join(src[j+1:j+60]))
        break
