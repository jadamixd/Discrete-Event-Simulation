import random
import matplotlib.pyplot as plt
import numpy as np

lambda_value = 0.5  # Intensity (arrival rate)
num_samples = 1000 

#random.expovariate gives us random pulls from the n.e.d 
x_samples = [(-(1/lambda_value)*np.log(random.uniform(0,1))) for sumthing_sumthing in range (num_samples)]
y_samples = [random.expovariate(lambda_value) for sumthin in range(num_samples)]

x_sorted = sorted(x_samples)
y_sorted = sorted(y_samples)

#Some fancy statistics to look at the correlation 
correlation = np.corrcoef(x_sorted, y_sorted)[0, 1]
print(f"Correlation: {correlation}")

plt.figure(figsize=(10, 6))
plt.plot(x_sorted, y_sorted, marker='o', linestyle='-', color='b', markersize=3, alpha=0.6)
plt.xlabel('X samples')
plt.ylabel('Y samples')
plt.title('Plot for X against Y')
plt.grid(True)
plt.show()