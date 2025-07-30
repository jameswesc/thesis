import concurrent.futures
import time
from functools import partial
from pathlib import Path

import geopandas as gpd
import pdal


def process_litree(
    site_plot_id: str, min_points=20, min_height=0.5, radius=100
) -> None:
    input_path = Path(f"data/plots/lidar/{site_plot_id}.copc.laz")
    output_path = Path(f"data/plots/lidar_litree/{site_plot_id}.copc.laz")

    if output_path.exists():
        print(f"Skipping {site_plot_id} as it already exists.")
        return None

    print(f"Clustering for {site_plot_id}")
    start_time = time.time()
    pl = (
        pdal.Reader(str(input_path))
        | pdal.Filter("filters.sort", dimension="HeightAboveGround", order="DESC")
        | pdal.Filter(
            "filters.litree",
            min_points=min_points,
            min_height=min_height,
            radius=radius,
        )
        | pdal.Writer(
            str(output_path),
            type="writers.copc",
            extra_dims="all",
        )
    )
    pl.execute()
    end_time = time.time()
    print(f"Clustering for {site_plot_id} took {end_time - start_time:,.2f} seconds")


MAX_WORKERS = 8

if __name__ == "__main__":
    start_time = time.time()
    # Get list of site_plot_ids
    plots = gpd.read_file("data/plots/plots.geo.json")
    site_plot_ids = plots["site_plot_id"].to_list()

    # Partially apply processing function with key word arguments
    process_func = partial(process_litree, min_points=20, min_height=0.5, radius=100)

    # Apply processing function in parallel
    with concurrent.futures.ProcessPoolExecutor(max_workers=MAX_WORKERS) as executor:
        executor.map(process_func, site_plot_ids)

    end_time = time.time()
    print(f"Total processing time took {end_time - start_time:,.2f} seconds")
