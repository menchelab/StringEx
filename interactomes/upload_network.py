import glob
import json
import os
import shutil

import requests

import src.settings as st
from src.classes import Evidences


def upload(
    organism: str,
    src: str,
    ip: str = "localhost",
    port: int = 5000,
) -> None:
    """Uploads the network using the internal upload route of the VRNetzer.

    Args:
        organism (str): Organism for which the layout files should be uploaded.
        ip (str): IP of the VRNetzer.
        port (int): Port of the VRNetzer.
        src (str): path directory, where the csv files are located.
    """
    layouts = []
    link_layouts = []
    src_dir = os.path.join(src, organism)
    nodes_dir = os.path.join(src_dir, "nodes")
    links_dir = os.path.join(src_dir, "links")
    layouts = [os.path.join(nodes_dir, file) for file in os.listdir(nodes_dir)]
    link_layouts = [os.path.join(links_dir, file) for file in os.listdir(links_dir)]
    for link_layout in link_layouts:
        if link_layout.endswith("any.csv"):
            tmp = link_layout
            link_layouts.remove(link_layout)
            link_layouts.append(tmp)
            break

    project_name = organism
    data = {"namespace": "New", "new_name": project_name}
    files = []
    for file in layouts:
        files.append(("layouts", open(file, "rb")))
    for file in link_layouts:
        files.append(("links", open(file, "rb")))
    st.log.info(f"Trying to upload network for {organism}.", flush=True)
    try:
        r = requests.post(f"http://{ip}:{port}/delpro?project={project_name}")
        r = requests.post(f"http://{ip}:{port}/uploadfiles", data=data, files=files)
        st.log.info(f"Uploaded network for {organism}.")
        st.log.debug(f"Response: {r}")

        network = os.path.join(src_dir, "links.pickle")
        pfile_path = os.path.join(st._PROJECTS_PATH, project_name, "pfile.json")

        with open(pfile_path, "r") as pfile:
            tmp = json.load(pfile)
        tmp["network_type"] = "ppi"
        tmp["network"] = "string"
        tmp["links"] = [f"{ev.value}XYZ" for ev in Evidences]
        tmp["linksRGB"] = [f"{ev.value}RGB" for ev in Evidences]
        with open(pfile_path, "w") as pfile:
            json.dump(tmp, pfile)

        # Move network.json.gzip to project folder
        shutil.copyfile(
            network, os.path.join(st._PROJECTS_PATH, project_name, "links.pickle")
        )

    except requests.exceptions.ConnectionError:
        st.log.error(f"Could not connect to {ip}:{port}. Upload failed.")
