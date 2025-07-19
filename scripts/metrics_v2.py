import geopandas
import pandas as pd
import pdal
import shapely
from cloud_metrics_v2 import calculate_cloud_metrics
from pandas import Series
from pixel_metrics_v2 import calculate_pixel_metrics, create_pixel_dataset
from voxel_metrics_v2 import calculate_voxel_metrics, create_voxel_dataset

# Params
veg_cutoff = 0.5
pixel_size = (1.0, 1.0)
voxel_size = (1.0, 1.0, 1.0)

skip_cloud_metrics = False
skip_pixel_metrics = False
skip_voxel_metrics = False


def calculate_metrics(row: Series):
    # Pull out plit ID, site and geometry and check they are valid
    site_plot_id = row.site_plot_id
    assert isinstance(site_plot_id, str), "A plot must have a site plot ID"

    site = row.site
    assert isinstance(site, str), "A plot must have a site"

    geometry = row.geometry
    assert isinstance(geometry, shapely.Polygon), "A plots geometry must be a polygon"

    # Read in points from lidar file
    lidar_file_name = f"data/plots/lidar/{site_plot_id}.copc.laz"
    pl = pdal.Reader(lidar_file_name, type="readers.copc").pipeline()
    pl.execute()

    points = pd.DataFrame(pl.arrays[0])

    if skip_cloud_metrics:
        print(f"Skipping cloud metrics for {site_plot_id}")
        cloud_metrics = pd.Series({})
    else:
        print(f"Calculating cloud metrics for {site_plot_id}")
        cloud_metrics = calculate_cloud_metrics(points, geometry, veg_cutoff=veg_cutoff)

    if skip_pixel_metrics:
        print(f"Skipping pixel metrics for {site_plot_id}")
        pixel_metrics = pd.Series({})
    else:
        print(f"Calculating pixel metrics for {site_plot_id}")
        pixels = create_pixel_dataset(
            points, veg_cutoff=veg_cutoff, pixel_size=pixel_size
        )
        pixels.to_netcdf(f"data/plots/netcdf/{site_plot_id}_pixels.nc")
        pixel_metrics = calculate_pixel_metrics(pixels)

    if skip_voxel_metrics:
        print(f"Skipping voxel metrics for {site_plot_id}")
        voxel_metrics = pd.Series({})
    else:
        print(f"Calculating voxel metrics for {site_plot_id}")
        voxels = create_voxel_dataset(points, voxel_size=voxel_size)
        voxel_metrics = calculate_voxel_metrics(voxels)
        voxels.to_netcdf(f"data/plots/netcdf/{site_plot_id}_voxels.nc")

    metrics = {**cloud_metrics, **pixel_metrics, **voxel_metrics}

    return pd.Series(metrics)


if __name__ == "__main__":
    # Read plots into geopandas dataframe
    plots = geopandas.read_file("data/plots/plots.geo.json")

    # Limit plots to the first 5 rows
    plots = plots.head(1)

    # Calculate metrics for each row
    metrics = plots.apply(calculate_metrics, axis=1)

    print(metrics)

    # Combine metrics with plot properties and drop geometry column
    # plots_with_metrics = pd.concat([plots, metrics], axis=1).drop(columns="geometry")

    # # Write to JSON file
    # plots_with_metrics.to_json("data/plots/metrics.json", orient="records", indent=4)

    # # Combine all metadata dictionaries into one
    # metrics_metadata = {
    #     **height_metrics_metadata,
    #     **openness_metrics_metadata,
    #     **exterior_metrics_metadata,
    #     **interior_metrics_metadata,
    #     **ancillary_metrics_metadata,
    # }

    # Save the combined metadata to a JSON file
    # json.dump(
    #     metrics_metadata,
    #     open("data/plots/metrics_metadata.json", "w"),
    #     indent=4,
    # )
