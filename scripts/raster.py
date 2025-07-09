import pdal


def dem(output_file: str, bounds: str | None = None) -> pdal.Writer:
    return pdal.Writer(
        output_file,
        type="writers.gdal",
        resolution=1,
        output_type="min",
        bounds=bounds,
        where="Classification == 2",
        data_type="float32",
    )


def dsm(output_file: str, bounds: str | None = None) -> pdal.Writer:
    return pdal.Writer(
        output_file,
        type="writers.gdal",
        resolution=1,
        output_type="max",
        bounds=bounds,
        data_type="float32",
    )


def chm(output_file: str, bounds: str | None = None) -> pdal.Writer:
    return pdal.Writer(
        output_file,
        type="writers.gdal",
        resolution=1,
        output_type="max",
        bounds=bounds,
        where="ReturnNumber == 1",
        dimension="HeightAboveGround",
        data_type="float32",
    )


def pulse_density(output_file: str, bounds: str | None = None) -> pdal.Writer:
    return pdal.Writer(
        output_file,
        type="writers.gdal",
        resolution=1,
        output_type="count",
        bounds=bounds,
        where="ReturnNumber == 1",
        binmode=True,
        nodata=0,
        data_type="float32",
    )


def point_density(output_file: str, bounds: str | None = None) -> pdal.Writer:
    return pdal.Writer(
        output_file,
        type="writers.gdal",
        resolution=1,
        output_type="count",
        bounds=bounds,
        binmode=True,
        nodata=0,
        data_type="float32",
    )


def scan_angle(output_file: str, bounds: str | None = None) -> pdal.Writer:
    return pdal.Writer(
        output_file,
        type="writers.gdal",
        resolution=1,
        output_type="mean",
        bounds=bounds,
        dimension="ScanAngleRank",
        data_type="float32",
    )


def create_rasters(
    input_file: str,
    dem_output_file: str | None = None,
    dsm_output_file: str | None = None,
    chm_output_file: str | None = None,
    pulse_density_output_file: str | None = None,
    point_density_output_file: str | None = None,
    scan_angle_output_file: str | None = None,
    bounds: str | None = None,
):
    pipeline = pdal.Reader(input_file).pipeline()
    if dem_output_file:
        pipeline |= dem(dem_output_file, bounds=bounds)
    if dsm_output_file:
        pipeline |= dsm(dsm_output_file, bounds=bounds)
    if chm_output_file:
        pipeline |= chm(chm_output_file, bounds=bounds)
    if pulse_density_output_file:
        pipeline |= pulse_density(pulse_density_output_file, bounds=bounds)
    if point_density_output_file:
        pipeline |= point_density(point_density_output_file, bounds=bounds)
    if scan_angle_output_file:
        pipeline |= scan_angle(scan_angle_output_file, bounds=bounds)

    count = pipeline.execute()
    return count, pipeline
