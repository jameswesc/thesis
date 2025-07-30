# %%
import geopandas as gpd

# %%
current_plots = gpd.read_file("data/plots/plots.geo.json")
all_plots = gpd.read_file("data/plots/allplots.geo.json")
current_plots.head()

# %%
all_plots["site_plot_id"] = (
    all_plots["site"] + "_P" + all_plots["plot_number"].astype(str)
)
# %%
all_plots.head()

# %%
current_plots.head()

# %%
missing_plots = all_plots[
    ~all_plots["site_plot_id"].isin(current_plots["site_plot_id"])
]
missing_plots.head()

# %%
len(missing_plots)

# %%
missing_plots.to_file("data/plots/missing_plots.geo.json", driver="GeoJSON")
