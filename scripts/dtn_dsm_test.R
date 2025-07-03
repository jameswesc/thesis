library(lidR)
library(terra)

las <- readLAS("data/sites/level-2/lidar/AGG_O_01.copc.laz", select = "xyzc")
dtm_tin <- rasterize_terrain(las, res = 1, algorithm = tin())
dtm_idw <- rasterize_terrain(las, res = 1, algorithm = knnidw(k = 10L, p = 2))

# Write rasters to file
writeRaster(dtm_tin, "data/sites/level-2/AGG_O_01_dtm_tin.tif", overwrite = TRUE)
writeRaster(dtm_idw, "data/sites/level-2/AGG_O_01_dtm_idw.tif", overwrite = TRUE)