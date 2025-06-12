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
    cat("Processing:", plot_info$site_plot_id, "\n")

    # Try to read and process the LAS file
    tryCatch({
      las <- readLAS(las_file)
      metrics <- cloud_metrics(las, .stdmetrics)

      # Create a row with plot info and metrics
      result_row <- data.frame(
        fid = plot_info$fid,
        site = plot_info$site,
        plot_number = plot_info$plot_number,
        site_type = plot_info$site_type,
        site_plot_id = plot_info$site_plot_id,
        metrics
      )

      # Append to results dataframe
      results_df <- rbind(results_df, result_row)

    }, error = function(e) {
      cat("Error processing", plot_info$site_plot_id, ":", conditionMessage(e), "\n")
    })

  } else {
    cat("File not found:", las_file, "\n")
  }
}

# Write results to JSON
write_json(results_df, "data/plot-metrics/std_metrics.json", pretty = TRUE)

cat("Processing complete. Results saved to data/plot-metrics/std_metrics.json\n")
cat("Total plots processed:", nrow(results_df), "\n")
