path = "/usr/local/lib/python3.12/site-packages/numpy/lib/_function_base_impl.py"
s = open(path).read()
i = s.find("def _compute_virtual_index")
print(s[i:i+900])
# and how the quantile uses virtual index (clamping etc.)
j = s.find("def _quantile_implementation")
print(s[j:j+500])
k = s.find("virtual_index", j)
print(s[k-200:k+3000])
