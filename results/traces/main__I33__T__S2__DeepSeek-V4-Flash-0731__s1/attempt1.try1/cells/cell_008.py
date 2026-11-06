
# Define the mapping function
cum_days = [0, 31, 60, 91, 121, 152, 182, 213, 244, 274, 305, 335]  # for months 1-12

def date_to_doy(year, month, day):
    return cum_days[month-1] + day

# Test
print(date_to_doy(2016, 1, 1))   # should be 1
print(date_to_doy(2016, 2, 28))  # should be 59
print(date_to_doy(2016, 2, 29))  # should be 60
print(date_to_doy(2016, 3, 1))   # should be 61
print(date_to_doy(2016, 12, 31)) # should be 366
print(date_to_doy(2015, 3, 1))   # should be 61 (non-leap)
print(date_to_doy(2015, 12, 31)) # should be 366 (non-leap)
