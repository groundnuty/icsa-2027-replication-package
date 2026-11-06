import inspect
import numpy.lib._function_base_impl as fb
s = inspect.getsource(fb)
for m in ["hazen", "inverted_cdf", "weibull"]:
    idx = 0
    while True:
        i = s.find(m, idx)
        if i == -1: break
        print("====", m, "@", i)
        print(s[max(0,i-300):i+500].replace("\n\n","\n"))
        print()
        idx = i + 1
        break
