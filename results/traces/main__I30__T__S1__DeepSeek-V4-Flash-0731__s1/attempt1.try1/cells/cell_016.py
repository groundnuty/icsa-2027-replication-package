
def day_of_year(month, day):
    month_days = [31, 29, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    return sum(month_days[:month-1]) + day

print(day_of_year(1, 1))    # 1
print(day_of_year(2, 28))   # 59
print(day_of_year(2, 29))   # 60
print(day_of_year(3, 1))    # 61
print(day_of_year(12, 31))  # 366
print(day_of_year(3, 2))    # 62
