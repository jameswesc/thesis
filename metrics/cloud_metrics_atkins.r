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
output_csv <-
  "../data/lidar-data/plots-cylce2-MGA2020/metrics_atkins_2023.csv"
output_json <-
  "../data/lidar-data/plots-cylce2-MGA2020/metrics_atkins_2023.json"

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
metrics <- NULL

canopy_cover_fn <- function(z) {
  n_total <- length(z)
  n_above_2m <- sum(z > 2)
  (n_above_2m / n_total) * 100
}

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

      plot_id <- base_name

      # Read LAS file (filter out points below zero)
      point_cloud <- readLAS(file_path, filter = "-drop_z_below 0")
      first_returns <- filter_first(point_cloud)

      # Calculate standard metrics
      z_mean <- cloud_metrics(point_cloud, func = ~ mean(Z))
      z_median <- cloud_metrics(point_cloud, func = ~ median(Z))
      z_max <- cloud_metrics(point_cloud, func = ~ max(Z))
      z_min <- cloud_metrics(point_cloud, func = ~ min(Z))

      ## Doble check FHD calc
      z_entropy <- cloud_metrics(point_cloud, func = ~ entropy(Z))
      fhd <- z_entropy * log(z_max)

      ## Used in canopy cover
      pct_above_2 <- cloud_metrics(point_cloud, func = ~ canopy_cover_fn(Z))

      # Used in MOCH and CRR_Fr
      z_fr_mean <- cloud_metrics(first_returns, func = ~ mean(Z))
      z_fr_max <- cloud_metrics(first_returns, func = ~ max(Z))
      z_fr_min <- cloud_metrics(first_returns, func = ~ min(Z))

      # Used in rugosity
      z_fr_sd <- cloud_metrics(first_returns, func = ~ sd(Z))

      # Canopy Relief Ratio (CRR) (Atkins et al. 2023)
      # Should this use all z? otherwise z_min will always be 0
      crr_all <- (z_mean - z_min) / (z_max - z_min)
      crr_fr <- (z_fr_mean - z_fr_min) / (z_fr_max - z_fr_min)

      # Extract site type
      site_type <- substr(base_name, 1, 3)

      # Create a new row and add it to the metrics dataframe
      new_row <- data.frame(
        plot_id = plot_id,
        mean_h = z_mean,
        median_h = z_median,
        moch = z_fr_mean,
        crr_all = crr_all,
        crr_fr = crr_fr,
        fhd = fhd,
        rugosity = z_fr_sd,
        cc = pct_above_2,
        site_type = site_type,
        stringsAsFactors = FALSE
      )

      # Add the row to the metrics dataframe
      metrics <- rbind(metrics, new_row)

      cat("Successfully processed metrics for", base_name, "\n")
    },
    error = function(e) {
      cat("Error processing", file_path, ":", e$message, "\n")
    }
  )
}
# %%
head(metrics)

# %%
# Write to CSV
output_file <- file.path(output_csv)
write.csv(metrics, output_file, row.names = FALSE)
cat("All metrics saved to", output_file, "\n")
cat("Total plots processed:", nrow(metrics), "\n")

# Write to JSON
output_file <- file.path(output_json)
json_data <- jsonlite::toJSON(metrics, pretty = TRUE)
writeLines(json_data, output_json)
cat("All metrics also saved to", output_json, "\n")
