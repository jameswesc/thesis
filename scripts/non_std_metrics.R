library(lidR)
library(jsonlite)
library(dplyr)
library(geometry)

# Read the plots data
plots_data <- fromJSON("data/loops/plots.json")

# Initialize an empty list to store results
results <- list()

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
            las <- readLAS(las_file, filter = "-drop_z_below 0")
            las_first <- filter_first(las)

            # TODO: Add metric calculations here
            zmax <- max(las$Z)

            # Create result for this plot
            new_result <- list(
                fid = as.numeric(plot_info$fid),
                site = as.character(plot_info$site),
                plot_number = as.numeric(plot_info$plot_number),
                site_type = as.character(plot_info$site_type),
                site_plot_id = as.character(plot_info$site_plot_id),
                vci = VCI(las$Z, zmax, by = 1),
                entropy = entropy(las$Z, zmax = zmax, by = 1),
                lad = LAD(las$Z, dz = 1, k = 0.5, z0 = 2),
                gap = gap_fraction_profile(las$Z, dz = 1, z0 = 2),
                rumple_index_first = rumple_index(las_first$X, las_first$Y, las_first$Z)
            )

            # Add to results list
            results[[length(results) + 1]] <- new_result

        }, error = function(e) {
            cat("Error processing", plot_info$site_plot_id, ":", conditionMessage(e), "\n")
        })

    } else {
        cat("File not found:", las_file, "\n")
    }
}

# Write results to JSON
write_json(results, "data/plot-metrics/non_std_metrics.json", pretty = TRUE, auto_unbox = TRUE)

cat("Processing complete. Results saved to data/plot-metrics/non_std_metrics.json\n")
cat("Total plots processed:", length(results), "\n")
