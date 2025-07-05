import pdal


def read_lidar(input_file: str):
    pipeline = pdal.Reader(input_file).pipeline()

    point_count = pipeline.eixecute()
    return point_count, pipeline
