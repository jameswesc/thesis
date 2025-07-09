# %%
import geopandas
import numpy as np
import pdal
import shapely

# %%
input_file = "data/sites/lidar/AGG_O_01.copc.laz"
plots_file = "data/plots/plots.geo.json"

# %%
plots = geopandas.read_file(plots_file).set_index("site_plot_id")
# %%
site_plots = plots[plots["site"] == "AGG_O_01"]

# %%
p5 = site_plots.loc["AGG_O_01_P5"]
p5_wkt = shapely.to_wkt(p5.geometry, 2)
# %%
pl = (
    pdal.Reader(input_file, type="readers.copc", polygon=p5_wkt)
    | pdal.Filter(type="filters.ferry", dimensions="HeightAboveGround => Z")
    | pdal.Filter(type="filters.range", limits="Z[0:]")
)
count = pl.execute()
count
# %%
points = pl.arrays[0]
Z = points["Z"]
np.quantile(Z, 0.5)

# %%
first_veg_returns = points[(points["ReturnNumber"] == 1) & (points["Z"] >= 0.5)]
first_veg_returns.shape
np.mean(first_veg_returns["Z"])
