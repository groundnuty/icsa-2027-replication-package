import numpy.lib._function_base_impl as F
print(F._QuantileMethods)
doc = F.quantile.__doc__
i = doc.find("hazen")
# print the section listing formulas
j = doc.find("The following")
print(doc[j:j+2500])
