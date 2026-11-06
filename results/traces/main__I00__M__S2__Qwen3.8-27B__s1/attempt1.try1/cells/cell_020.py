path = "/usr/local/lib/python3.12/site-packages/numpy/_core/function_base.py"
src = open(path).read()
i = src.find("hazen")
print(src[i-3500:i+2500])
