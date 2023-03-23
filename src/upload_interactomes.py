import json

import pandas as pd
import requests
from project import Project

from . import settings as st
from .classes import Evidences
import os


def upload(data: dict, files: dict) -> None:
    """Updated the interactome project which where just uploaded with additional annotations.

    Args:
        data (dict): dictionary with the project name and the host.
        files (dict): dictionary with the files containing the nodes annotations, links annotations and cluster labels.
    """
    host = data["host"]
    project_name = data["project_name"]
    files = files.to_dict(flat=False)
    nodes = json.loads(files.pop("nodes_data")[0].read().decode("UTF-8"))
    links = json.loads(files.pop("links_data")[0].read().decode("UTF-8"))
    clusters = None
    if "cluster_labels" in files:
        clusters = json.loads(files.pop("cluster_labels")[0].read().decode("UTF-8"))

    try:
        project = Project(project_name)

        project.pfile["network_type"] = "ppi"
        project.pfile["network"] = "string"
        if clusters:
            project.pfile["selections"] = clusters
        # ignored_layout_rgb = [
        #     color
        #     for color in project.pfile["layoutsRGB"]
        #     if any(x in color for x in ["springRGB", "localRGB", "globalRGB"])
        # ]
        # project.pfile["layoutsRGB"] = [
        #     color
        #     for color in project.pfile["layoutsRGB"]
        #     if color not in ignored_layout_rgb
        # ]

        project.pfile["links"] = [f"{ev}XYZ" for ev in Evidences.get_all_evidences()]
        project.pfile["linksRGB"] = [f"{ev}RGB" for ev in Evidences.get_all_evidences()]
        project.write_pfile()

        project.nodes = {"nodes": nodes}
        project.links = {"links": links}
        project.write_nodes()
        project.write_links()
        # for file in os.listdir(project.layouts_rgb_dir):
        #     if any(x in file for x in ignored_layout_rgb):
        #         os.remove(os.path.join(project.layouts_rgb_dir, file))

    except requests.exceptions.ConnectionError:
        st.log.error(f"Could not connect to {host}. Upload failed.")
    return "Upload successful."
