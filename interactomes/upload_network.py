import glob
import json
import os
import tarfile

import requests

import src.settings as st
import src.util as util
from src.classes import Evidences


def upload(organism: str,src:str, dest:str, ip:str="localhost", port:int=5000) -> None:
    """Uploads the network using the internal upload route of the VRNetzer.

    Args:
        organism (str): Organism for which the layout files should be uploaded.
        ip (str): IP of the VRNetzer.
        port (int): Port of the VRNetzer.
        src (str): path to .tgz file.
        dest (str): path directory, where to unpack the .tgz file.
    """
    file_name = os.path.join(src, f"{organism}.tgz")
    dest = os.path.join(dest, organism)
    with tarfile.open(file_name, "r:gz") as tar:
        for file in tar.getmembers():
            if file.name.endswith(".csv"):
                file.name = os.path.basename(file.name)
                tar.extract(file, dest)
    layouts = []
    link_layouts=[]
    for f in glob.glob(os.path.join(dest,"*")):
        if f.endswith("node.csv"):
            layouts.append(f)
        for l in [ev.value for ev in Evidences]:
            if f.endswith(f"{l}.csv"):
                link_layouts.append(f)
    project_name = organism
    data = {"namespace":"New",
        "new_name":project_name}
    files = []
    for file in layouts:
        files.append(("layouts", open(file,"rb")))
    for file in link_layouts:
        files.append(("links",open(file,"rb")))

    r = requests.post(f"http://{ip}:{port}/uploadfiles",data = data,files=files)
    st.log.info(f"Uploaded network for {organism}.")
    st.log.debug(f"Response: {r}")

    pfile_path = os.path.join(st._PROJECTS_PATH,project_name,"pfile.json")
    with open(pfile_path,"r") as pfile:
        tmp = json.load(pfile)
    tmp["network_type"] = "ppi"
    tmp["network"] = "string"
    with open(pfile_path,"w") as pfile:
        json.dump(tmp,pfile)