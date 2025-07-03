# Noise test
library(lidR)

las <- readLAS("data/sites/lidar-MGA94/EPY_Y_04.laz", select = "xyzc")
mean <- mean(las$Z)
sd <- sd(las$Z)

noisey_points <- sum(las$Z > mean + 6 * sd | las$Z < mean - 6 * sd)

print("Noisey points")
print(noisey_points)