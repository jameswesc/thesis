import laspy
import numpy as np

file = "data/plots/lidar-normalised/AGG_O_01_P1.copc.laz"

with laspy.open(file) as fh:
    print("Points from Header:", fh.header.point_count)
    las = fh.read()
    print(las)
    print("Points from data:", len(las.points))
    ground_pts = las.classification == 2
    bins, counts = np.unique(las.return_number[ground_pts], return_counts=True)  # pyright: ignore
    print("Ground Point Return Number distribution:")
    for r, c in zip(bins, counts):
        print("    {}:{}".format(r, c))
