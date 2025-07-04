from os import path

import click
import geopandas
import pdal


@click.command()
@click.option("--site", required=True, help="Site identifier")
@click.option("--data-dir", default="data", help="Data directory path (default: data)")
def preprocess_site(site, data_dir):
    """Preprocess LiDAR data for a given site."""

    sites_file = path.join(data_dir, "sites/sites.geo.json")
    input_file = path.join(data_dir, "sites/lidar-MGA94", f"{site}.laz")
    output_file = path.join(data_dir, "sites/lidar", f"{site}.copc.laz")

    sites_gdf = geopandas.read_file(sites_file).set_index("site")

    polygon_wkt = sites_gdf.loc[site].polygon_wkt

    pipeline = (
        pdal.Reader(input_file)
        | pdal.Filter(type="filters.reprojection", out_srs="EPSG:7855")
        | pdal.Filter(type="filters.crop", polygon=polygon_wkt)
        | pdal.Filter(
            type="filters.outlier", method="statistical", mean_k=6, multiplier=10
        )
        | pdal.Filter(type="filters.range", limits="Classification[0:5]")
        | pdal.Filter(type="filters.hag_nn", allow_extrapolation=False, count=1)
        | pdal.Writer(output_file, type="writers.copc")
    )

    print(f"Preprocessing site: {site}")
    points = pipeline.execute()
    print(f"\t{site} processed with {points:,d} points")


if __name__ == "__main__":
    preprocess_site()
