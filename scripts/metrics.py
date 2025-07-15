import json

import geopandas
import pandas as pd
import pdal
import rasterio
import shapely
from ancillary_metrics import ancillary_metrics_metadata, calculate_ancillary_metrics
from exterior_metrics import calculate_exterior_metrics, exterior_metrics_metadata
from height_metrics import calculate_height_metrics, height_metrics_metadata
from interior_metrics import calculate_interior_metrics, interior_metrics_metadata
from openness_metrics import calculate_openness_metrics, openness_metrics_metadata
from pandas import Series
from rasterio.mask import mask


def calculate_metrics(row: Series):
    # Pull out plit ID, site and geometry and check they are valid
    site_plot_id = row.site_plot_id
    assert isinstance(site_plot_id, str), "A plot must have a site plot ID"

    print(f"Calculating metrics for {site_plot_id}")

    site = row.site
    assert isinstance(site, str), "A plot must have a site"

    geometry = row.geometry
    assert isinstance(geometry, shapely.Polygon), "A plots geometry must be a polygon"
    polygon_wkt = shapely.to_wkt(geometry, 2)

    # Read in points from lidar file
    lidar_file_name = f"data/sites/lidar/{site}.copc.laz"
    pl = pdal.Reader(
        lidar_file_name, type="readers.copc", polygon=polygon_wkt
    ).pipeline()
    pl.execute()
    points = pl.arrays[0]

    # Read in CHM pixels
    chm_file_name = f"data/sites/raster/{site}_chm.tif"
    with rasterio.open(chm_file_name) as chm_src:
        masked_data, masked_transform = mask(
            chm_src, [geometry], crop=True, nodata=chm_src.nodata
        )

        chm = masked_data[0]
        # Remove nodata pixels
        chm = chm[chm != chm_src.nodata]

    # Read in SD of height pixels
    sdh_file = f"data/sites/raster/{site}_sdh.tif"
    with rasterio.open(sdh_file) as sdh_src:
        masked_data, masked_transform = mask(
            sdh_src, [geometry], crop=True, nodata=sdh_src.nodata
        )

        sdh = masked_data[0]
        # Remove nodata pixels
        sdh = sdh[sdh != sdh_src.nodata]

    # Calculate metrics
    height_metrics = calculate_height_metrics(points, chm)
    openness_metrics = calculate_openness_metrics(points, chm)
    exterior_metrics = calculate_exterior_metrics(chm)
    interior_metrics = calculate_interior_metrics(points, sdh)
    ancillary_metrics = calculate_ancillary_metrics(points, geometry)

    # Combine metrics
    metrics = pd.concat(
        [
            height_metrics,
            openness_metrics,
            exterior_metrics,
            interior_metrics,
            ancillary_metrics,
        ]
    )

    return metrics


if __name__ == "__main__":
    # Read plots into geopandas dataframe
    plots = geopandas.read_file("data/plots/plots.geo.json")

    # Calculate metrics for each row
    metrics = plots.apply(calculate_metrics, axis=1)

    # Combine metrics with plot properties and drop geometry column
    plots_with_metrics = pd.concat([plots, metrics], axis=1).drop(columns="geometry")

    # Write to JSON file
    plots_with_metrics.to_json("data/plots/metrics.json", orient="records", indent=4)

    # Combine all metadata dictionaries into one
    metrics_metadata = {
        **height_metrics_metadata,
        **openness_metrics_metadata,
        **exterior_metrics_metadata,
        **interior_metrics_metadata,
        **ancillary_metrics_metadata,
    }

    # Save the combined metadata to a JSON file
    json.dump(
        metrics_metadata,
        open("data/plots/metrics_metadata.json", "w"),
        indent=4,
    )
