# %%
import geopandas

# %%
input_file = "data/sites/lidar/AGG_O_01.copc.laz"
plots_file = "data/plots/plots.geo.json"

# %%
plots = geopandas.read_file(plots_file).set_index("site_plot_id")
# del plots["polygon_wkt"]
del plots["ploygon_wkt"]
# %%
plots.to_file("data/plots/plots.geo.json", driver="GeoJSON")
