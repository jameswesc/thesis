library(lidR)
library(jsonlite)
library(dplyr)

# Read the plots data
plots_data <- fromJSON("data/loops/plots.json")

# Initialize an empty dataframe to store results
results_df <- data.frame()

# Loop through each plot
for (i in 1:nrow(plots_data)) {
  plot_info <- plots_data[i, ]

  # Construct the file path
  las_file <- paste0("data/lidar-plots-copc/", plot_info$site_plot_id, ".copc.laz")

  # Check if file exists before processing
  if (file.exists(las_file)) {
    # cat("Processing:", plot_info$site_plot_id, "\n")

    # Try to read and process the LAS file
    tryCatch({
      las <- readLAS(las_file)
      las <- classify_noise(las, ivf(5,1))

      noise_count <- sum(las$Classification == 18)
      if (noise_count > 0) {
        cat(plot_info$site_plot_id, "Classified ", noise_count, " points as noise\n")
      }


    }, error = function(e) {
      cat("Error processing", plot_info$site_plot_id, ":", conditionMessage(e), "\n")
    })

  } else {
    cat("File not found:", las_file, "\n")
  }
}
