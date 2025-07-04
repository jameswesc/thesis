# %%
import json

import pdal

# %%
site = "PPO_Y_07"

site_file = f"../data/sites/lidar/{site}.copc.laz"

# %%
pipeline = pdal.Reader(site_file, type="readers.copc") | pdal.Filter(
    type="filters.info"
)
pipeline.execute()
# %%
print(json.dumps(pipeline.metadata, indent=2))
