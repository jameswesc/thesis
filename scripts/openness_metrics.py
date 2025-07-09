import geopandas
import pandas as pd
import pdal
import rasterio
import shapely
from numpy.typing import NDArray
from rasterio.mask import mask

openness_metrics_metadata = {
    "proportion_above_2": {
        "title": "Proportion Above 2m",
        "description": "Number of points with height above ground > 2, divided by total number of points",
        "unit": "unitless fraction",
        "category": "openness",
    },
    "deep_gap_fraction_05": {
        "title": "Deep Gap Fraction (0.5m)",
        "description": "Number of gap pixels in CHM divided by total number of pixel. A gap is a pixel with a height <= 0.5 m",
        "unit": "unitless fraction",
        "category": "openness",
    },
    "deep_gap_fraction_2": {
        "title": "Deep Gap Fraction (2m)",
        "description": "Number of gap pixels in CHM divided by total number of pixel. A gap is a pixel with a height <= 2 m",
        "unit": "unitless fraction",
        "category": "openness",
    },
    "gap_fraction_profile": {
        "title": "Gap Fraction Profile",
        "description": "Gap fraction profile - vertical distribution of gaps",
        "unit": "unitless",
        "category": "openness",
    },
}


def calculate_openness_metrics(points: NDArray, chm: NDArray):
    Z = points["HeightAboveGround"]
    Z_above_2 = points[points["HeightAboveGround"] > 2]

    proportion_above_2 = len(Z_above_2) / len(Z)

    # Gaps are points below height threshold in CHM
    gaps_05 = chm[chm <= 0.5]
    gaps_2 = chm[chm <= 2]

    deep_gap_fraction_05 = len(gaps_05) / len(chm)
    deep_gap_fraction_2 = len(gaps_2) / len(chm)

    # TODO: Calculate gap fraction profile
    # For now, using placeholder value
    metrics = {
        "proportion_above_2": proportion_above_2,
        "deep_gap_fraction_05": deep_gap_fraction_05,
        "deep_gap_fraction_2": deep_gap_fraction_2,
        "gap_fraction_profile": -999,  # Placeholder
    }

    return pd.Series(metrics, dtype=float)


if __name__ == "__main__":
    plots = geopandas.read_file("data/plots/plots.geo.json")
    plot = plots.iloc[0]
    site = plot.site
    geometry = plot.geometry
    polygon_wkt = shapely.to_wkt(geometry, 2)
    lidar_file = f"data/sites/lidar/{site}.copc.laz"
    chm_file = f"data/sites/raster/{site}_chm.tif"

    pl = pdal.Reader(lidar_file, type="readers.copc", polygon=polygon_wkt).pipeline()
    pl.execute()
    points = pl.arrays[0]

    with rasterio.open(chm_file) as chm_src:
        masked_data, masked_transform = mask(
            chm_src, [geometry], crop=True, nodata=chm_src.nodata
        )

        chm = masked_data[0]
        # Remove nodata pixels
        chm = chm[chm != chm_src.nodata]

    print(calculate_openness_metrics(points=points, chm=chm))
