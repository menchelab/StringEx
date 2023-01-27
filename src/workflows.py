import glob
import gzip
import json
import os
import shutil
import time
import traceback

import flask

from . import util as string_util
from .classes import Evidences, Organisms
from .converter import VRNetzConverter
from .layouter import Layouter
from .map_small_on_large import map_source_to_target
from .settings import _NETWORKS_PATH, _PROJECTS_PATH, UNIPROT_MAP, log
from .uploader import Uploader


def VRNetzer_upload_workflow(
    network: dict,
    filename: str,
    project_name: str,
    algo: str = "string",
    tags: dict = None,
    algo_variables: dict = None,
    layout_name: str = None,
    project_path: str = None,
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

    if not project_name:
        return "namespace fail"

    # create layout
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
    network = layouter.network

    # upload network
    uploader = Uploader(
        network,
        p_path=project_path,
        p_name=project_name,
        stringify=tags.get("stringify"),
        overwrite_project=overwrite_project,
    )
    s1 = time.time()
    state = uploader.upload_files(network)
    log.debug(f"Uploading process took {time.time()-s1} seconds.")
    if tags.get("string_write"):
        outfile = f"{_NETWORKS_PATH}/{project_name}_processed.VRNetz"
        with open(outfile, "w") as f:
            json.dump(network, f)
        log.info(f"Saved network as {outfile}")
    if tags.get("stringify"):
        uploader.stringify_project()
        log.debug("Layouts of project has been stringified.")
    log.debug(f"Total process took {time.time()-s1} seconds.")
    log.info("Project has been uploaded!")
    html = (
        f'<a style="color:green;"href="/StringEx/preview?project={project_name}">SUCCESS: Network {filename} saved as project {project_name} </a><br>'
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
    network_file = os.path.join(f_organ, "network.json.gzip")

    with open(nodes_file, "r") as json_file:
        trg_network = json.load(json_file)
    with gzip.open(network_file, "r") as fin:
        json_bytes = fin.read()
        json_str = json_bytes.decode("utf-8")
        trg_network["links"] = json.loads(json_str)["all_links"]
    src_network = Layouter.gen_evidence_layouts(src_network)
    if project_name is None or project_name == "":
        src_name = os.path.split(src_filename)[1].split(".")[0]
        trg_name = organism.replace(".", "_")
        project_name = f"{src_name}_on_{trg_name}"
    if "ppi" not in project_name.lower():
        # Add ppi to project name to activate the right node panel
        project_name = f"{project_name}_ppi"
    try:
        shutil.copytree(
            f_organ, os.path.join(_PROJECTS_PATH, project_name), dirs_exist_ok=True
        )
        for dir in ["links", "linksRGB"]:
            for file in glob.glob(os.path.join(_PROJECTS_PATH, project_name, dir, "*")):
                for ev in Evidences:
                    if ev.value in file:
                        os.remove(file)
        with open(os.path.join(f_organ, "pfile.json"), "r") as f:
            pfile = json.load(f)
            pfile["name"] = project_name
            pfile["network"] = "string"
        with open(
            os.path.join(os.path.join(_PROJECTS_PATH, project_name), "pfile.json"), "w"
        ) as f:
            json.dump(pfile, f)

        html = map_source_to_target(src_network, trg_network, f_organ, project_name)

    except Exception as e:
        error = traceback.format_exc()
        log.error(error)
        html = f'<a style="color:red;">ERROR </a>: {error}', 500
    return html


def VRNetzer_send_network_workflow(request: dict):
    network = {
        "nodes": request.pop("nodes"),
        "links": request.pop("links"),
        "layouts": request.pop("layouts"),
    }
    form = request.pop("form")
    layout_name = form.get("layout")
    to_running = form.get("load")
    algo = form["algorithm"]["n"]
    algo_variables = string_util.get_algo_variables(algo, form)

    network_data = request.get("network")
    # enrichments = request.get("enrichments")
    # publications = request.get("publications")

    project_name = form["project"]
    overwrite_project = form["update"]

    tags = {
        "stringify": False,
        "string_write": False,
        "string_calc_lay": True,
    }
    if network_data.get("database") == "string":
        tags["stringify"] = True

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
            flask.current_app.socketio.emit(
                "ex",
                {"id": "projects", "opt": project_name, "fn": "sel"},
                namespace="/chat",
                room=flask.session.get("room"),
            )
    output = output.split("<br>")
    output.pop(0)
    data = {"html": "<br>".join(output)}

    return json.dumps(data)


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
        layouter.network = network
        nodes = layouter.network["nodes"]
        links = layouter.network["links"]
        layouter.gen_graph(nodes, links)
    else:
        layouter.read_from_vrnetz(network)
        log.info(f"Network extracted from: {network}")

    if gen_layout:
        log.info(f"Applying algorithm {layout_algo} ...")
        layout = layouter.apply_layout(layout_algo, algo_variables)[0]
        layouter.add_layout_to_vrnetz(layout, layout_name)
        if layout_algo is None:
            layout_algo = "spring"
        log.info(f"Layout algorithm {layout_algo} applied!")
    # Correct Cytoscape positions to be positive.
    # if cy_layout:
    #     layouter.correct_cytoscape_pos()
    #     log.info(f"2D layout created!")
    if stringify:
        log.info("Will Stringify.")
        layouter.network = Layouter.gen_evidence_layouts(layouter.network)
        log.info(f"Layouts stringified!")
    else:
        log.info("Will NOT Stringify.")
        layouter.network = Layouter.add_any_link_layout(layouter.network)
        log.info(f"Layout Any added")
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
    if stringifiy and cy_layout:
        uploader.stringify_project()
        log.info(f"Layouts stringified: {project_name}")
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
