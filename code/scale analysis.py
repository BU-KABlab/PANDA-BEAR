import numpy as np

ten_sec_array = np.loadtxt("data/scale_testing_01_appfilt_finalrd_platetype3_ten_sec.txt")
five_sec_array = np.loadtxt("data/scale_testing_01_appfilt_finalrd_platetype3_five_sec.txt")
three_sec_array = np.loadtxt("data/scale_testing_01_appfilt_finalrd_platetype3_three_sec.txt")

ten_sec_variance = np.var(ten_sec_array)
five_sec_variance = np.var(five_sec_array)
three_sec_variance = np.var(three_sec_array)

print("10s variance: ", ten_sec_variance)
print("5s variance: ", five_sec_variance)
print("3s variance: ", three_sec_variance)
