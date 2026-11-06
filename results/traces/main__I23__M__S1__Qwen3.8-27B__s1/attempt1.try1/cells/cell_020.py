import numpy.lib._function_base_impl as fb, inspect
print(inspect.getsource(fb._compute_virtual_index))
print(inspect.getsource(fb._inverted_cdf))
print(inspect.getsource(fb._closest_observation))
