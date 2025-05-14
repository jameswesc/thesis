# %%
# Load required libraries
if (!requireNamespace("lidR", quietly = TRUE)) {
  install.packages("lidR")
}
library("lidR")

if (!requireNamespace("dplyr", quietly = TRUE)) {
  install.packages("dplyr")
}
library("dplyr")

# Define input and output directories
input_dir <-
  "../data/lidar-data/plots-cylce2-MGA2020"
output_dir <- "../data/lidar-data/plots-cylce2-MGA2020"

# %%
# Get all .laz files in the input directory
laz_files <- list.files(
  path = input_dir,
  pattern = "\\.copc\\.laz$",
  full.names = TRUE
)

# Check if any files were found
if (length(laz_files) == 0) {
  cat("No .laz files found in", input_dir, "\n")
} else {
  cat("Found", length(laz_files), ".laz files to process\n")
}

# %%
# Process each file
for (file_path in laz_files) {
  # Try to read the LAS file with error handling
  tryCatch(
    {
      # Extract base filename without extension for use as plot_id
      # Peform twice because files are .copc.laz
      base_name <- tools::file_path_sans_ext(
        tools::file_path_sans_ext(basename(file_path))
      )

      # Read LAS file (filter out points below zero)
      # Take x,y,z (implicity), i = intensity, r = return number
      # n = number of returns, RGBN = red, green, blue & nir,
      # and c = classification
      point_cloud <- readLAS(file_path,
        select = "irnRGBNc", filter = "-drop_z_below 0"
      )

      # Extract points to data frame
      points_df <- point_cloud@data

      # Create output filename
      output_file <- file.path(output_dir, paste0(base_name, ".csv"))

      # Write to CSV
      write.csv(points_df, output_file, row.names = FALSE)

      cat("Written", base_name, "to CSV\n")
    },
    error = function(e) {
      cat("Error processing", file_path, ":", e$message, "\n")
    }
  )
}
