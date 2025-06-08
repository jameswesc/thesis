# Python Scripts

This folder contains scripts for processing lidar data for my thesis.

## Create Site Directories

A command-line tool for preprocessing lidar files and creating site directories with filtered GeoJSON plot data.

```bash
uv run create_site_directories.py --lidar-directory <path> --plots <path> --output-dir <path>
```

### Arguments

- `--lidar-directory`: Directory containing lidar files with naming pattern `[SITE].laz` (required)
- `--plots`: GeoJSON file containing plot data (required)
- `--output-dir`: Output directory path (required)
- `--max-sites`: Maximum number of sites to process (optional, if not provided all sites will be processed)
- `--overwrite`: Overwrite existing output directory and files without confirmation (optional)

### What the Script Does

For each lidar file `[SITE].laz` found in the input directory:

1. **Creates site directory**: `output_dir/[SITE]/`
2. **Processes lidar file with PDAL**:
   - Reprojects from input CRS to EPSG:7855 (MGA 2020 Zone 55)
   - Classifies statistical outliers as low noise (7)
   - Computes height above ground using nearest neighbor interpolation (`filters.hag_nn` with default settings)
   - Saves as `[SITE]_MGA2020.copc.laz` in Cloud Optimized Point Cloud format
3. **Creates filtered plots**: `[SITE]_plots_MGA2020.geojson` containing only plots matching the site name

### Lidar Directory Structure
```
lidar_files/
├── AGG_O_01.laz
├── AGG_O_05.laz
├── EPO_O_04.laz
└── ...
```

### GeoJSON Plot File Format
The plots GeoJSON file should contain features with properties including:
- `site`: Site identifier matching the lidar filename
- `plot_number`: Plot number within the site
- `site_type`: Type of site (e.g., "AGG", "EPO")

Example feature:
```json
{
  "type": "Feature",
  "properties": {
    "fid": 1,
    "site": "AGG_O_01",
    "plot_number": 1,
    "site_type": "AGG"
  },
  "geometry": { ... }
}
```

### Output Structure

```
output_dir/
├── AGG_O_01/
│   ├── AGG_O_01_MGA2020.copc.laz
│   └── AGG_O_01_plots_MGA2020.geojson
├── AGG_O_05/
│   ├── AGG_O_05_MGA2020.copc.laz
│   └── AGG_O_05_plots_MGA2020.geojson
└── EPO_O_04/
    ├── EPO_O_04_MGA2020.copc.laz
    └── EPO_O_04_plots_MGA2020.geojson
```

### PDAL Processing Pipeline

The script uses PDAL to process each lidar file through the following steps:

1. **Read**: Load input LAZ file
2. **Reproject**: Transform coordinates to EPSG:7855 (MGA 2020 Zone 55)
3. **Statistical Outlier Removal**: Classify statistical outliers as low noise (7)
4. **Height Above Ground**: Compute using nearest neighbor interpolation with default settings
5. **Write**: Save as COPC LAZ format with HeightAboveGround as extra dimension

### Example Usage

```bash
# Process all sites
uv run create_site_directories.py --lidar-directory ./raw_lidar --plots ./plots.geojson --output-dir ./processed_sites

# Process only first 5 sites
uv run create_site_directories.py --lidar-directory ./raw_lidar --plots ./plots.geojson --output-dir ./processed_sites --max-sites 5

# Overwrite existing output directory without confirmation
uv run create_site_directories.py --lidar-directory ./raw_lidar --plots ./plots.geojson --output-dir ./processed_sites --overwrite

# Combine options
uv run create_site_directories.py --lidar-directory ./raw_lidar --plots ./plots.geojson --output-dir ./processed_sites --max-sites 3 --overwrite
```

### Error Handling

- Script validates that input directories exist and contain expected files
- Checks for existing output directory and prompts for confirmation (unless --overwrite is used)
- Provides detailed error messages and full traceback for PDAL processing errors
- Reports processing statistics including success/failure counts and total points processed
- Continues processing remaining sites if individual sites fail

### Dependencies

- `click`: Command-line interface
- `pdal`: Point cloud processing library
- `pathlib`: Path handling
- `json`: JSON file processing
- `shutil`: File operations

Make sure PDAL is properly installed and configured in your environment before running the script.

## Prepare Lidar Data (Deprecated)

**Note**: This script has been merged into `create_site_directories.py`. The standalone `prepare_lidar_data.py` script is no longer needed as the combined workflow is more efficient.

The PDAL processing functionality from this script is now integrated into the site directory creation process, eliminating the need for a separate processing step.
