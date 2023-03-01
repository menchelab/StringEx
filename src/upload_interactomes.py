import json

import pandas as pd
import requests
from project import Project

from . import settings as st
from .classes import Evidences


def upload(data: dict, files) -> None:
    """Uploads the network using the internal upload route of the VRNetzer.

    Args:
        directory (str): directory in which the layout files are located.
        ip (str): IP of the VRNetzer.
        port (int): Port of the VRNetzer.
        src (str): path directory, where the csv files are located.
    """
    host = data["host"]
    project_name = data["project_name"]
    files = files.to_dict(flat=False)
    nodes = json.loads(files.pop("nodes_data")[0].read().decode("UTF-8"))
    links = json.loads(files.pop("links_data")[0].read().decode("UTF-8"))

    try:
        project = Project(project_name)

        project.pfile["network_type"] = "ppi"
        project.pfile["network"] = "string"
        project.pfile["links"] = [f"{ev.value}XYZ" for ev in Evidences]
        project.pfile["linksRGB"] = [f"{ev.value}RGB" for ev in Evidences]
        project.write_pfile()

        project.nodes = {"nodes": nodes}
        project.links = {"links": links}
        project.write_nodes()
        project.write_links()

    except requests.exceptions.ConnectionError:
        st.log.error(f"Could not connect to {host}. Upload failed.")
    return "Upload successful."
