import geopandas
import numpy as np
import pandas as pd
import rasterio
from numpy.typing import NDArray
from rasterio.mask import mask

exterior_metrics_metadata = {
    "top_rugosity": {
        "title": "Top Rugosity",
        "description": "Standard deviation of 1m² canopy height model",
        "unit": "m",
        "category": "exterior",
    },
    "rumple_index": {
        "title": "Rumple Index",
        "description": "Rumple index - ratio of canopy surface area to ground surface area",
        "unit": "unitless",
        "category": "exterior",
    },
}


def calculate_exterior_metrics(chm: NDArray):
    top_rugosity = np.std(chm)

    # TODO: Calculate rumple index
    # For now, using placeholder value
    metrics = {
        "top_rugosity": top_rugosity,
        "rumple_index": -999,  # Placeholder
    }

    return pd.Series(metrics, dtype=float)


if __name__ == "__main__":
    plots = geopandas.read_file("data/plots/plots.geo.json")
    plot = plots.iloc[0]
    site = plot.site
    geometry = plot.geometry
    chm_file = f"data/sites/raster/{site}_chm.tif"

    with rasterio.open(chm_file) as chm_src:
        masked_data, masked_transform = mask(
            chm_src, [geometry], crop=True, nodata=chm_src.nodata
        )

        chm = masked_data[0]
        # Remove nodata pixels
        chm = chm[chm != chm_src.nodata]

    print(calculate_exterior_metrics(chm=chm))
