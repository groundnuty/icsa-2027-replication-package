import inspect
from numpy.lib import _function_base_impl as fb
src = inspect.getsource(fb._quantile_ureduce_func)
import re
# find the linear/hazen interpolation part
i = src.find("virtual_interpolation")
print(src[i:i+1500] if i>=0 else "not found; searching 'hazen'...")
for m in re.finditer(r"hazen", src):
    print("----")
    print(src[m.start()-200:m.start()+400])