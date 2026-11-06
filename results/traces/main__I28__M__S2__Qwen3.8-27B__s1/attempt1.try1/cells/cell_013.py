p = "/usr/local/lib/python3.12/site-packages/numpy/lib/_function_base_impl.py"
src = open(p).read().splitlines()
for i,l in enumerate(src):
    if "_compute_virtual_index" in l and "def " in l:
        print("\n".join(src[i-15:i+25]))
        break
# also doc table around 4392
print("---- doc table ----")
print("\n".join(src[4380:4410]))
