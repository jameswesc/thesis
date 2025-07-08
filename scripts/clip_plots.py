import geopandas
import pdal
import shapely

sites = geopandas.read_file("data/sites/sites.geo.json").set_index("site")
plots = geopandas.read_file("data/plots/plots.geo.json").set_index("site_plot_id")


for site_id, site_feature in sites.iterrows():
    input_file = f"data/sites/lidar/{site_id}.copc.laz"

    site_plots = plots[plots["site"] == site_id]
    for plot_id, plot_feature in site_plots.iterrows():
        output_file = f"data/plots/lidar/{plot_id}.copc.laz"
        polygon_wkt = shapely.to_wkt(plot_feature.geometry, 2)
        pl = (
            pdal.Reader(input_file, type="readers.copc", polygon=polygon_wkt)
            | pdal.Filter(
                type="filters.ferry", dimensions="Z => Altitude, HeightAboveGround => Z"
            )
            | pdal.Filter(type="filters.range", limits="Z[0:]")
            | pdal.Writer(
                output_file,
                type="writers.copc",
                forward="scale,offset",
                extra_dims="all",
            )
        )
        count = pl.execute()
        print(f"Clipped {count:,d} points from {input_file} to {output_file}.")
