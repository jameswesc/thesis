library(lidR)
library(sf)
library(tidyverse)
library(jsonlite)

# Parse command line arguments
args <- commandArgs(trailingOnly = TRUE)
base_dir <- "../sites" # default value

if (length(args) > 0) {
    for (i in seq_along(args)) {
        if (args[i] == "--base_dir" && i < length(args)) {
            base_dir <- args[i + 1]
        }
    }
}

process_site <- function(site) {
    site_dir <- str_c(base_dir, "/", site)
    lidar_file <- str_c(site_dir, "/", site, "_MGA2020_HN_LN.copc.laz")
    plots_file <- str_c(site_dir, "/", site, "_plots_MGA2020.geojson")

    # Read in lidar data
    lidar_data <- readLAS(
        lidar_file,
        filter = "-drop_class 18"
    )
    lidar_data <- filter_poi(lidar_data, Z >= 0)

    # Read in plots data
    plots <- st_read(plots_file, quiet = TRUE)

    # Calculate std_z_metrics
    std_z_metrics <- plot_metrics(
        lidar_data,
        ~ stdmetrics_z(Z, zmin = 0, dz = 1, th = 2),
        plots
    )

    # Filter out low noise (classification 7)
    lidar_data <- filter_poi(lidar_data, Classification != 7)

    # Recompute std_z_metrics
    std_z_metrics_nolownoise <- plot_metrics(
        lidar_data,
        ~ stdmetrics_z(Z, zmin = 0, dz = 1, th = 2),
        plots
    )

    list(
        std_z_metrics = std_z_metrics,
        std_z_metrics_nolownoise = std_z_metrics_nolownoise
    )
}


sites <- list.dirs(base_dir, full.names = FALSE, recursive = FALSE)

# # Initialize combined dataframes
# all_std_z_metrics <- data.frame()
# all_std_z_metrics_nolownoise <- data.frame()

site <- "ULM_80"
metrics <- process_site(site)
write_json(
    st_drop_geometry(metrics$std_z_metrics),
    str_c(base_dir, "/", site, "/", site, "_std_z_metrics.json")
)
write_json(
    st_drop_geometry(metrics$std_z_metrics_nolownoise),
    str_c(base_dir, "/", site, "/", site, "_std_z_metrics_nolownoise.json")
)

# for (i in seq_along(sites)) {
#     site <- sites[i]
#     print(str_c("Processing ", site, " ... ", i, "/", length(sites)))
#     metrics <- process_site(site)

#     # Add site column if it isn't there
#     if (!"site" %in% names(metrics$std_z_metrics)) {
#         metrics$std_z_metrics$site <- site
#     }
#     if (!"site" %in% names(metrics$std_z_metrics_nolownoise)) {
#         metrics$std_z_metrics_nolownoise$site <- site
#     }

#     # Write out metrics as json for individual sites
#     write_json(
#         st_drop_geometry(metrics$std_z_metrics),
#         str_c(base_dir, "/", site, "/", site, "_std_z_metrics.json")
#     )
#     write_json(
#         st_drop_geometry(metrics$std_z_metrics_nolownoise),
#         str_c(base_dir, "/", site, "/", site, "_std_z_metrics_nolownoise.json")
#     )

#     # Add to total metrics
#     all_std_z_metrics <- bind_rows(
#         all_std_z_metrics, st_drop_geometry(metrics$std_z_metrics)
#     )
#     all_std_z_metrics_nolownoise <- bind_rows(
#         all_std_z_metrics_nolownoise, st_drop_geometry(metrics$std_z_metrics_nolownoise)
#     )
# }

# # Write combined dataframes to JSON files
# write_json(
#     all_std_z_metrics,
#     str_c(base_dir, "/allsites_std_z_metrics.json")
# )
# write_json(
#     all_std_z_metrics_nolownoise,
#     str_c(base_dir, "/allsites_std_z_metrics_nolownoise.json")
# )
