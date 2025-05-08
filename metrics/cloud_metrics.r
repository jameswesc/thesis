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
  "/Users/jgregory/Code/thesis/metrics/data/lidar-data/plots-cylce2-MGA2020"
output_csv <- "std_metrics.csv"
output_json <- "std_metrics.json"

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
# Initialize an empty dataframe to hold all metrics
all_metrics <- NULL

# Process each file
for (file_path in laz_files) {
  # Extract base filename without extension for use as plot_id
  base_name <- tools::file_path_sans_ext(basename(file_path))
  # Peform twice because files are .copc.laz
  base_name <- tools::file_path_sans_ext(base_name)
  print(base_name)

  cat("Processing", file_path, "\n")
  # Try to read the LAS file with error handling
  tryCatch(
    {
      # Read LAS file (filter out points below zero)
      las <- readLAS(file_path, filter = "-drop_z_below 0")

      # Calculate standard metrics
      metrics <- cloud_metrics(las, func = .stdmetrics)

      # Convert metrics to dataframe and unlist values to get scalar values
      metrics_df <- as.data.frame(
        lapply(metrics, function(x) if (length(x) == 1) unlist(x) else x)
      )

      # Add plot_id column
      metrics_df$plot_id <- base_name

      # Append to the all_metrics dataframe
      if (is.null(all_metrics)) {
        all_metrics <- metrics_df
      } else {
        all_metrics <- rbind(all_metrics, metrics_df)
      }

      cat("Successfully processed metrics for", base_name, "\n")
    },
    error = function(e) {
      cat("Error processing", file_path, ":", e$message, "\n")
    }
  )
}

if (!is.null(all_metrics) && nrow(all_metrics) > 0) {
  # Move plot_id to the first column
  all_metrics <- all_metrics %>% select(plot_id, everything())
} else {
  cat("No metrics were processed. Check if input files exist and are valid.\n")
}
# %%
head(all_metrics)

# %%
# Write to CSV
output_file <- file.path(output_csv)
write.csv(all_metrics, output_file, row.names = FALSE)
cat("All metrics saved to", output_file, "\n")
cat("Total plots processed:", nrow(all_metrics), "\n")

# Write to JSON
output_file <- file.path(output_json)
json_data <- jsonlite::toJSON(all_metrics, pretty = TRUE)
writeLines(json_data, output_json)
cat("All metrics also saved to", output_json, "\n")
