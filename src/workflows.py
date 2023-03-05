import glob
import json
import os
import pickle
import shutil
import time
import traceback

import flask
import pandas as pd

from . import util as string_util
from .classes import Evidences
from .classes import LinkTags as LiT
from .classes import Organisms
from .classes import VRNetzElements as VRNE
from .converter import VRNetzConverter
from .layouter import Layouter
from .map_small_on_large import map_source_to_target
from .settings import _NETWORKS_PATH, _PROJECTS_PATH, UNIPROT_MAP, log
from .uploader import Uploader
from project import Project


def VRNetzer_upload_workflow(
    network: dict,
    filename: str,
    project_name: str,
    algo: str = "string",
    tags: dict = None,
    algo_variables: dict = None,
    layout_name: str = None,
    overwrite_project: bool = False,
) -> str:
    """Used from the StringEX/uploadfiles route to upload VRNetz networks to the VRNetzer.

    Args:
        network (dict): Loaded network (loaded with json.load).
        filename (str): Name of the network file which is uploaded
        project_name (str): Name of the project to be created.
        algo(str,optional): Name of the layout algorithm to be used. Defaults to "string".
        tags (dict,optional): Dictionary of tags to options in underlying functions. Defaults to None.
        cg_variables (dict, optional): dictionary containing varaibles for cartoGRAPHs variables. Defaults to None.

    Returns:
        str: HTML string to reflect whether the upload was successful or not.
    """
    if type(network) is dict:
        network[VRNE.nodes] = pd.DataFrame(network[VRNE.nodes])
        network[VRNE.links] = pd.DataFrame(network[VRNE.links])
    if tags is None:
        tags = {
            "stringify": False,
            "string_write": False,
            "string_calc_lay": False,
        }

    if algo_variables is None:
        algo_variables = {}
    log.info("Starting upload of VRNetz...")
    start = time.time()

    log.debug(f"Network loaded in {time.time()-start} seconds.")
    log.info(f"Network loaded from {filename}.", flush=True)

    if not project_name:
        return "namespace fail"

    # create layout
    log.info(f"Applying layout algorithm:{algo}", flush=True)
    s1 = time.time()
    layouter = apply_layout_workflow(
        network,
        layout_algo=algo,
        stringify=tags.get("stringify"),
        gen_layout=tags.get("string_calc_lay"),
        algo_variables=algo_variables,
        layout_name=layout_name,
    )
    log.debug(f"Applying layout algorithm in {time.time()-s1} seconds.")
    log.info(f"Applied layout algorithm:{algo}", flush=True)
    network = layouter.network
    # upload network
    uploader = Uploader(
        network,
        p_name=project_name,
        stringify=tags.get("stringify"),
        overwrite_project=overwrite_project,
    )
    s1 = time.time()
    state = uploader.upload_files(network)
    log.debug(f"Uploading process took {time.time()-s1} seconds.")
    log.info(f"Uploading network...", flush=True)
    if tags.get("string_write"):
        outfile = f"{_NETWORKS_PATH}/{project_name}_processed.VRNetz"
        os.makedirs(os.path.dirname(outfile), exist_ok=True)
        with open(outfile, "w") as f:
            json.dump(network, f)
        log.info(f"Saved network as {outfile}")
    log.debug(f"Total process took {time.time()-s1} seconds.", flush=True)
    log.info("Project has been uploaded!")
    html = (
        f'<a style="color:green;"href="/StringEx/preview?project={project_name}" target="_blank" >SUCCESS: Network {filename} saved as project {project_name} </a><br>'
        + state
    )

    return html


def VRNetzer_map_workflow(
    src_network: dict,
    src_filename: str,
    organism: str,
    project_name: str,
):
    """Used from the StringEX/mapfiles route to map a small String network onto a large String network prepared in the VRNetzer.

    Args:
        network (dict): Loaded network (loaded with json.load).
        src_filename (str):  Name of the network file which is to be mapped.
        organism (str): Name of the organism from which the network originates from.
        project_name (str):  Name of the project to be created.

    Returns:
        str: HTML string to reflect whether the mapping was successful or not.
    """

    log.info("Starting mapping of VRNetz...")

    f_organ = Organisms.get_file_name(organism)
    f_organ = os.path.join(_PROJECTS_PATH, f_organ)

    nodes_file = os.path.join(f_organ, "nodes.json")
    links_file = os.path.join(f_organ, "links.json")

    with open(nodes_file, "r") as json_file:
        trg_network = json.load(json_file)

    with open(links_file, "r") as json_file:
        trg_network[VRNE.links] = json.load(json_file)["links"]

    # trg_network[VRNE.links]["id"] = trg_network["links"].index
    # trg_network[VRNE.links] = trg_network["links"].to_dict("records")

    if project_name is None or project_name == "":
        src_name = os.path.split(src_filename)[1].split(".")[0]
        trg_name = organism.replace(".", "_")
        project_name = f"{src_name}_on_{trg_name}"
    if "ppi" not in project_name.lower():
        # Add ppi to project name to activate the right node panel
        project_name = f"{project_name}_ppi"
    try:
        src = Project(f_organ)
        project = Project(project_name, False)
        src.copy(project.location, ignore=False)
        project.read_pfile()
        for ev in Evidences:
            links = [ev.value + "XYZ" for ev in Evidences]
            link_colors = [ev.value + "RGB" for ev in Evidences]
            project.pfile["links"] = links
            project.pfile["linksRGB"] = link_colors
        # for dir in ["links", "linksRGB"]:
        #     for file in glob.glob(os.path.join(_PROJECTS_PATH, project_name, dir, "*")):
        #         for ev in Evidences:
        #             if ev.value in file:
        #                 os.remove(file)

        project.pfile["name"] = project_name
        project.write_pfile()

        start = time.time()
        html = map_source_to_target(src_network, trg_network, f_organ, project_name)
        log.debug(f"Mapping process took {time.time()-start} seconds.")

    except Exception as e:
        error = traceback.format_exc()
        log.error(error)
        project.remove()
        html = f'<a style="color:red;">ERROR </a>: {error}', 500
    return html


def VRNetzer_send_network_workflow(request: dict, blueprint):
    network = {
        "nodes": request.pop("nodes"),
        "links": request.pop("links"),
        "layouts": request.pop("layouts"),
    }
    form = request.get("form")
    layout_name = form.get("layout")
    to_running = form.get("load")
    algo = form["algorithm"]["n"]
    algo_variables = string_util.get_algo_variables(algo, form["algorithm"])
    network_data = request.get("network")
    # enrichments = request.get("enrichments")
    # publications = request.get("publications")

    project_name = form["project"]
    overwrite_project = form["update"]
    if overwrite_project == "Update":
        overwrite_project = False
    else:
        overwrite_project = True
    tags = {
        "stringify": False,
        "string_write": False,
        "string_calc_lay": True,
    }
    if network_data.get("database") in ["string", "stitch"]:
        tags["stringify"] = True
    log.debug(f"STRINGIFY {tags['stringify']}")
    output = VRNetzer_upload_workflow(
        network,
        project_name,
        project_name,
        algo,
        tags,
        algo_variables,
        layout_name,
        overwrite_project=overwrite_project,
    )
    if to_running:
        for i in range(2):
            blueprint.emit(
                "ex",
                {"id": "projects", "opt": project_name, "fn": "sel"},
                namespace="/chat",
                room=flask.session.get("room"),
            )
    return output[1:]


def apply_layout_workflow(
    network: str,
    gen_layout: bool = True,
    layout_algo: str = None,
    cy_layout: bool = True,
    stringify: bool = True,
    algo_variables: dict = {},
    layout_name: str = None,
) -> Layouter:
    layouter = Layouter()
    if type(network) is dict:
        network[VRNE.nodes] = pd.DataFrame(network[VRNE.nodes])
        network[VRNE.links] = pd.DataFrame(network[VRNE.links])
        layouter.network = network
        layouter.graph = layouter.gen_graph(network[VRNE.nodes], network[VRNE.links])
    else:
        layouter.read_from_vrnetz(network)
        log.info(f"Network extracted from: {network}")

    if gen_layout:
        if layout_algo is None:
            layout_algo = "spring"
        log.info(f"Applying algorithm {layout_algo} ...")
        layout = layouter.apply_layout(layout_algo, algo_variables)
        algo, layout = next(iter(layout.items()))
        nodes = layouter.add_layout_to_vrnetz(
            layouter.network[VRNE.nodes], layout, layout_name
        )
        layouter.network[VRNE.nodes] = nodes
        log.info(f"Layout algorithm {layout_algo} applied!")
    links = Layouter.gen_evidence_layouts(
        layouter.network[VRNE.links], stringify=stringify
    )
    drops = ["s_suid", "e_suid"]
    for c in drops:
        if c in links.columns:
            links = links.drop(columns=[c])
    layouter.network[VRNE.links] = links
    return layouter


def create_project_workflow(
    network: dict,
    project_name: str,
    projects_path: str = _PROJECTS_PATH,
    skip_exists: bool = False,
    keep_tmp: bool = False,
    cy_layout: bool = True,
    stringifiy: bool = True,
):
    """Uses a layout to generate a new VRNetzer Project."""
    uploader = Uploader(network, project_name, skip_exists, stringifiy, projects_path)
    state = uploader.upload_files(network)
    if keep_tmp:
        outfile = f"{_NETWORKS_PATH}/{project_name}_with_3D_Coords.VRNetz"
        print(f"OUTFILE:{outfile}")
        with open(outfile, "w") as f:
            json.dump(network, f)
        log.info(f"Saved network as {outfile}")
    log.info(f"Project created: {project_name}")
    return state


def map_workflow(small_net: str, large_net: str, destination: str) -> None:
    """Maps a small network onto a large network."""
    map_source_to_target(small_net, large_net, destination)


def convert_workflow(
    node_list: str, edge_list: str, uniprot_mapping=None, project=None
) -> str:
    """Converts a network from a edge and node list to a .VRNetz file."""
    if uniprot_mapping is None:
        uniprot_mapping = UNIPROT_MAP
    if project is None:
        project = "NA"
    output = os.path.join(_NETWORKS_PATH, project)
    converter = VRNetzConverter(node_list, edge_list, uniprot_mapping, project)
    converter.convert()
    return output
