# %%
library(lidR)
library(sf)
library(tidyverse)
library(jsonlite)

# %%
base_dir <- "../sites"
# %%
process_site <- function(site) {
    site_dir <- str_c(base_dir, "/", site)
    lidar_file <- str_c(site_dir, "/", site, "_MGA2020.copc.laz")
    plots_file <- str_c(site_dir, "/", site, "_plots_MGA2020.geojson")

    # Read in lidar data
    lidar_data <- readLAS(
        lidar_file,
        filter = "-drop_class 18"
    )
    lidar_data <- filter_poi(lidar_data, HeightAboveGround >= 0)

    # Read in plots data
    plots <- st_read(plots_file, quiet = TRUE)

    # Calculate std_z_metrics
    std_z_metrics <- plot_metrics(
        lidar_data,
        ~ stdmetrics_z(HeightAboveGround, zmin = 0, dz = 1, th = 2),
        plots
    )

    # Filter out low noise (classification 7)
    lidar_data <- filter_poi(lidar_data, Classification != 7)

    # Recompute std_z_metrics
    std_z_metrics_nolownoise <- plot_metrics(
        lidar_data,
        ~ stdmetrics_z(HeightAboveGround, zmin = 0, dz = 1, th = 2),
        plots
    )

    list(
        std_z_metrics = std_z_metrics,
        std_z_metrics_nolownoise = std_z_metrics_nolownoise
    )
}

# %%
write_out_metrics <- function(metrics, site) {
    site_dir <- str_c(base_dir, "/", site)
    write_json(
        st_drop_geometry(metrics$std_z_metrics),
        str_c(site_dir, "/", site, "_std_z_metrics.json")
    )
    write_json(
        st_drop_geometry(metrics$std_z_metrics_nolownoise),
        str_c(site_dir, "/", site, "_std_z_metrics_nolownoise.json")
    )
}
# %%
site <- "AGG_O_01"
metrics <- process_site(site)
metrics


# %%
sites <- list.dirs(base_dir, full.names = FALSE, recursive = FALSE)
for (site in sites) {
    print(str_c("Processing ", site))
    metrics <- process_site(site)
    write_out_metrics(metrics, site)
}
