import os

import networkx as nx
import numpy
import numpy as np
import open3d as o3d

_WORKING_DIR = os.path.dirname(os.path.abspath(__file__))
_THIS_EXT = os.path.join(_WORKING_DIR, "..")
_THIS_EXT_STATIC_PATH = os.path.join(
    _WORKING_DIR, "..", "static"
)  # Static path of this extension

SPHERE = os.path.join(_THIS_EXT_STATIC_PATH, "resources", "sphere.ply")


def sample_sphere_pcd(
    SAMPLE_POINTS=100,
    layout: list[list[float, float, float]] = [],
    debug=False,
) -> numpy.array:
    """Utility function to sample points from a sphere. Can be used for functional layouts for node with no annotations.

    Args:
        SAMPLE_POINTS (int, optional): Number of points to sample. Defaults to 100.
        layout (list, optional): List of points if the calculated Layout. Is used to center the sphere around this layout. Defaults to [].
        debug (bool, optional): Switch to show visualization of the process. Defaults to False.

    Returns:
        numpy.array: Array of sampled points with shape (SAMPLE_POINTS, 3)
    """
    if SAMPLE_POINTS == 0:
        return numpy.array([])
    # get protein name & read mesh as .ply format
    mesh = o3d.io.read_triangle_mesh(SPHERE)
    mesh.compute_vertex_normals()
    layout_pcd = o3d.geometry.PointCloud()
    layout_pcd.points = o3d.utility.Vector3dVector(numpy.asarray(layout))
    layout_pcd.paint_uniform_color([1, 0, 0])
    layout_center = layout_pcd.get_center()
    mesh.translate(layout_center, relative=False)
    pcd = mesh.sample_points_uniformly(number_of_points=SAMPLE_POINTS)
    pcd.paint_uniform_color([0, 1, 0])
    if debug:
        o3d.visualization.draw_geometries([pcd, layout_pcd])
    return numpy.asarray(pcd.points)


def visualize_layout(
    layout: list[list[float, float, float]],
    colors: list[list[float, float, float]],
    screenshot=False,
    png_name="screenshot.png",
) -> None:
    """Visualize a layout with colors in 3D using open3D.

    Args:
        layout (list[list[float, float, float]]): List of points with shape (n, 3)
        colors (list[list[float, float, float]]): List of colors of the points with shape (n, 3)

    Returns:
        None: None
    """
    pcd = o3d.geometry.PointCloud()
    pcd.points = o3d.utility.Vector3dVector(numpy.asarray(layout))
    pcd.colors = o3d.utility.Vector3dVector(numpy.asarray(colors))

    def change_background_to_black(vis):
        opt = vis.get_render_option()
        opt.background_color = np.asarray([0, 0, 0])
        return False

    def change_background_to_white(vis):
        opt = vis.get_render_option()
        opt.background_color = np.asarray([1, 1, 1])
        return False

    key_to_callback = {}
    key_to_callback[ord("K")] = change_background_to_black
    key_to_callback[ord("L")] = change_background_to_white
    key_to_callback[ord("P")] = exit

    try:
        o3d.visualization.draw_geometries_with_key_callbacks([pcd], key_to_callback)
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    some_graph = nx.complete_graph(500)
    pos = nx.spring_layout(some_graph, dim=3)
    pos = list(pos.values())
    sample_sphere_pcd(layout=pos, debug=True)
