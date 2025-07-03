library(lidR)
library(leafR)

file <- "data/plots/lidar-normalised/AGG_O_01_P1.copc.laz"
las <- readLAS(file)

voxels <- leafR::lad.voxels(file, grain.size = 5, k = 1)
lad_profile <- lad.profile(voxels)

lai <- lai(lad_profile)

vox <- lidR::voxelize_points(las, res = c(5, 1))

length(las$Z)
length(vox$Z)
sum(vox$Z == 17)

lidR::writeLAS(vox, "AGG_O_01_P1_voxels.laz")