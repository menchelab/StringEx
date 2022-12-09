import json
import logging
import os
import shutil
import time
import traceback

import flask

from .converter import VRNetzConverter

# from .cytoscape_parser import CytoscapeParser
from .layouter import Layouter
from .map_small_on_large import map_source_to_target
from .settings import _NETWORKS_PATH, _PROJECTS_PATH, UNIPROT_MAP, Organisms, log

# from .settings import VRNetzElements as VRNE
# from .string_commands import (StringCompoundQuery, StringDiseaseQuery,
#                               StringProteinQuery, StringPubMedQuery)
from .uploader import Uploader

# import networkx as nx


# from extract_colors_from_style import get_node_mapping


def VRNetzer_upload_workflow(
    network: dict,
    filename: str,
    project_name: str,
    algo: str = "string",
    tags: dict = None,
    cg_variables: dict = None,
    project_path: str = None,
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

    if cg_variables is None:
        cg_variables = {
            "prplxty": 50,
            "density": 0.5,
            "l_rate": 200,
            "steps": 1000,
            "n_neighbors": 15,
            "spread": 1.0,
            "min_dist": 0.0,
        }

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
        cg_variables=cg_variables,
    )
    log.debug(f"Applying layout algorithm in {time.time()-s1} seconds.")
    network = layouter.network

    # upload network
    uploader = Uploader(
        network,
        p_path=project_path,
        p_name=project_name,
        stringify=tags.get("stringify"),
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
        f'<a style="color:green;" href="/StringEx/preview?project={project_name}">SUCCESS: Network {filename} saved as project {project_name} </a><br>'
        + state
    )

    return html


def VRNetzer_map_workflow(
    network: dict,
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
    print(nodes_file)
    with open(nodes_file, "r") as json_file:
        trg_network = json.load(json_file)
    with open(links_file, "r") as json_file:
        trg_network["links"] = json.load(json_file)["links"]

    layouter = Layouter()
    layouter.network = src_network
    layouter.gen_evidence_layouts()
    src_network = layouter.network
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
        with open(os.path.join(f_organ, "pfile.json"), "r") as json_file:
            pfile = json.load(json_file)
            pfile["name"] = project_name
            pfile["network"] = "string"
        with open(
            os.path.join(os.path.join(_PROJECTS_PATH, project_name), "pfile.json"), "w"
        ) as json_file:
            json.dump(pfile, json_file)

        map_source_to_target(src_network, trg_network, f_organ, project_name)
        html = f'<a style="color:green;" href="/StringEx/preview?project={project_name}">SUCCESS: network {src_filename} mapped on {organism} saved as project {project_name} </a>'
    except Exception as e:
        error = traceback.format_exc()
        log.error(error)
        html = f'<a style="color:red;">ERROR </a>: {error}', 500
    return html


def apply_layout_workflow(
    network: str,
    gen_layout: bool = True,
    layout_algo: str = None,
    cy_layout: bool = True,
    stringify: bool = True,
    cg_variables: dict = {},
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
        layouter.apply_layout(layout_algo, cg_variables)
        if layout_algo is None:
            layout_algo = "spring"
        log.info(f"Layout algorithm {layout_algo} applied!")
    # Correct Cytoscape positions to be positive.
    # if cy_layout:
    #     layouter.correct_cytoscape_pos()
    #     log.info(f"2D layout created!")
    if stringify:
        log.info("Will Stringify.")
        layouter.gen_evidence_layouts()
        log.info(f"Layouts stringified!")
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


# def apply_style_workflow(graph: nx.Graph, style: str) -> nx.Graph:
#     color_mapping = get_node_mapping(style)
#     if color_mapping is None:
#         return graph
#     mapping_type = color_mapping["type"]
#     log.info(
#         f"Color mapping extracted from: {style}.xml. Mapping Type: {mapping_type}"
#     )
#     graph = colorize_nodes(graph, color_mapping)
#     log.info(f"Colored nodes according to color mapping.")
#     return graph

# def protein_query_workflow(
#     parser: CytoscapeParser, p_query: list[str], **kwargs
# ) -> None:
#     """Fetches a network for given protein query."""
#     query = StringProteinQuery(query=p_query, **kwargs)
#     log.info(f"Command as list:{query.cmd_list}")
#     parser.exec_cmd(query.cmd_list)


# def disease_query_workflow(parser: CytoscapeParser, disease: str, **kwargs) -> None:
#     """Fetches a network for given disease query."""
#     query = StringDiseaseQuery(disease=disease, **kwargs)
#     log.info(f"Command as list:{query.cmd_list}")
#     parser.exec_cmd(query.cmd_list)


# def compound_query_workflow(
#     parser: CytoscapeParser, query: list[str], **kwargs
# ) -> None:
#     """Fetches a network for given compound query."""
#     query = StringCompoundQuery(query=query, **kwargs)
#     log.info(f"Command as list:{query.cmd_list}")
#     parser.exec_cmd(query.cmd_list)


# def pubmed_query_workflow(parser: CytoscapeParser, pubmed: list[str], **kwargs) -> None:
#     """Fetches a network for given pubmed query."""
#     query = StringPubMedQuery(pubmed=pubmed, **kwargs)
#     log.info(f"Command as list:{query.cmd_list}")
#     parser.exec_cmd(query.cmd_list)
#     print(query.cmd_list)


# def export_network_workflow(
#     parser: CytoscapeParser,
#     filename: str = None,
#     network: str = None,
#     keep_output: bool = True,
#     layout_algo: str = None,
#     **kwargs,
# ) -> tuple[Layouter, str]:
#     """Exports a network as GraphML file, generates a 3D layout."""
#     networks = parser.get_network_list()
#     if network is None:
#         network = list(networks.keys())[0]
#     if filename is None:
#         filename = network
#     filename = filename.replace(" ", "_")
#     network_loc = f"{_NETWORKS_PATH}/{filename}"
#     network_file = f"{network_loc}.VRNetz"

#     parser.export_network(filename=network_loc)
#     log.info(f"Network exported: {network}")

#     # generate a 3D layout
#     layouter = apply_layout_workflow(f"{network_loc}.VRNetz", layout_algo)

#     # if keep_output is False, we remove the tmp GraphML file
#     if not keep_output:
#         os.remove(network_file)
#         log.info(f"Removed tmp file: {network_file}")

#     return layouter, filename


# TODO: Networkx export with separate table export. Does not work do fails in matching node/edge names to SUIDs
# def parse_network(parser: CytoscapeParser, network_index=None, **kwargs):
#     if network_index is None:
#         network_index = 0
#     networks = parser.get_network_list()
#     network = list(networks.keys())[network_index]
#     graph = parser.get_networkx_network(network)
#     # node_columns, edge_columns = parser.export_table(network)
#     nx.draw(graph)
#     plt.show()


# TODO directly create a networkx network
