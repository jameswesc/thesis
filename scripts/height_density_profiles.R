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
            totalZ = length(las$Z)
            zMax = max(las$Z)

            # Create height density profile with 1-meter intervals
            max_interval <- ceiling(zMax)
            height_profile <- list()

            for (z in 0:(max_interval - 1)) {
                zmin <- z
                zmax <- z + 1

                # For the last interval, include points exactly at zMax
                if (zmax >= zMax) {
                    point_count <- sum(las$Z >= zmin & las$Z <= zMax)
                } else {
                    point_count <- sum(las$Z >= zmin & las$Z < zmax)
                }

                proportion <- point_count / totalZ

                # Only include intervals that have points
                if (proportion > 0) {
                    height_profile[[length(height_profile) + 1]] <- list(
                        zmin = zmin,
                        zmax = zmax,
                        proportion = proportion
                    )
                }
            }

            # Create result for this plot
            new_result <- list(
                fid = as.numeric(plot_info$fid),
                site = as.character(plot_info$site),
                plot_number = as.numeric(plot_info$plot_number),
                site_type = as.character(plot_info$site_type),
                site_plot_id = as.character(plot_info$site_plot_id),
                height_profile = height_profile
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
write_json(results, "data/plot-metrics/height_density_profile_1m.json", pretty = TRUE, auto_unbox = TRUE)

cat("Processing complete. Results saved to data/plot-metrics/height_density_profile_1m.json\n")
cat("Total plots processed:", length(results), "\n")
