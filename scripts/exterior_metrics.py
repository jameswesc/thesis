import json

import geopandas
import numpy as np
import pandas as pd
import rasterio
import shapely
from pandas import Series
from rasterio.mask import mask

plots = geopandas.read_file("data/plots/plots.geo.json")
sites = geopandas.read_file("data/sites/sites.geo.json")


def calculate_exterior_metrics(row: Series):
    site_plot_id = row.site_plot_id
    assert isinstance(site_plot_id, str), "A plot must have a site plot ID"

    print(f"Calculating metrics for {site_plot_id}")

    site = row.site
    assert isinstance(site, str), "A plot must have a site"

    geometry = row.geometry
    assert isinstance(geometry, shapely.Polygon), "A plots geometry must be a polygon"

    chm_file_name = f"data/sites/raster/{site}_chm.tif"

    with rasterio.open(chm_file_name) as chm:
        masked_data, masked_transform = mask(
            chm, [geometry], crop=True, nodata=chm.nodata
        )

        chm_data = masked_data[0]
        # Remove nodata pixels
        chm_data = chm_data[chm_data != chm.nodata]
        top_rugosity = np.std(chm_data)

    metrics = {"top_rugosity": top_rugosity, "rumple_index": -999}

    return pd.Series(metrics, dtype=float)


exterior_metrics = plots.apply(calculate_exterior_metrics, axis=1)
plots_with_exterior_metrics = pd.concat([plots, exterior_metrics], axis=1).drop(
    columns="geometry"
)
plots_with_exterior_metrics.to_json(
    "data/plots/exterior_metrics.json", orient="records", indent=4
)

exterior_metrics_metadata = {
    "top_rugosity": "Standard deviation of 1m² canopy height model (Unit: m)",
    "rumple_index": "TODO",
}

json.dump(
    exterior_metrics_metadata,
    open("data/plots/exterior_metrics_metadata.json", "w"),
    indent=4,
)
