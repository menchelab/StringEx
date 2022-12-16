import glob
import gzip
import json
import os
import sys
import tarfile

import networkx as nx
import numpy as np
import pandas

from src import settings as st
from src.classes import Evidences
from src.classes import LinkTags as LiT
from src.classes import NodeTags as NT
from src.classes import Organisms
from src.layouter import Layouter


def construct_graph(
    networks_directory: str, organism: str, last_link: int or None = None
):
    """Extracts data from the STRING DB network files and constructs a nx.Graph afterwards.

    Args:
        networks_directory (str): Path to directory where the STRING DB network files are stored for the given organism.
        organism (str): Organism from which the network originates from.
        last_link (int o rNone, optional): FOR DEBUGGING: Integer of the last link to be processed. Defaults to None.

    Returns:
        tuple[nx.Graph, dict]: Graph representing the protein-protein interaction network and a dictionary containing the nodes of the graph.
    """
    link_file, alias_file, description_file = "", "", ""
    directory = os.path.join(networks_directory, organism)
    for file in glob.glob(os.path.join(directory, "*")):
        if file.endswith("protein.links.detailed.v11.5.txt"):
            link_file = file
        elif file.endswith(".protein.aliases.v11.5.txt"):
            alias_file = file
        elif file.endswith(".protein.info.v11.5.txt"):
            description_file = file
    network_table = pandas.read_table(link_file, header=0, sep=" ")
    alias_table = pandas.read_table(
        alias_file,
        header=0,
        sep="\t",
        index_col=0,
    )
    description_table = pandas.read_table(
        description_file, header=0, sep="\t", index_col=0
    )
    return gen_graph(network_table, alias_table, description_table, organism, last_link)


def gen_graph(
    network_table: pandas.DataFrame,
    alias_table: pandas.DataFrame,
    description_table: pandas.DataFrame,
    organism: str,
    last_link: int or None = None,
) -> tuple[nx.Graph, dict]:
    """Extracts data from the STRING database files and constructs a graph representing the protein-protein interaction network.

    Args:
        network_table (pandas.DataFrame): Data Frame containing all links of the network.
        alias_table (spandas.DataFrametr): Data Frame containing all aliases of the proteins.
        description_table (pandas.DataFrame): Data Frame containing Descriptions of the proteins.
        organism (str): Organism from which the network originates from.
        last_link (int or None, optional): FOR DEBUGGING: Integer of the last link to be processed. Defaults to None.

    Returns:
        tuple[nx.Graph, dict]: Graph representing the protein-protein interaction network and a dictionary containing the nodes of the graph.
    """

    species = Organisms.get_scientific_name(organism)
    G = nx.Graph()
    nodes_in = {}
    next_id = 0
    ev_columns = [
        "neighborhood",
        "fusion",
        "cooccurence",
        "coexpression",
        "experimental",
        "database",
        "textmining",
    ]
    if last_link is None:
        last_link = len(network_table)

    color_scheme = Evidences.get_default_scheme()
    l_lays = {ev: [] for ev in color_scheme}

    for idx in range(last_link):
        row = network_table.iloc[idx]
        link = {}
        s_node = {}
        e_node = {}
        start = row.get("protein1")
        end = row.get("protein2")
        if start is None or end is None:
            continue

        if start not in nodes_in:

            s_node[NT.id] = int(next_id)
            next_id += 1
            s_node[NT.name] = start.split(".")[1]

            # get uniprot id(s)
            alias = alias_table.loc[start]
            s_node["uniprot"] = list(
                alias.loc[alias["source"] == "Ensembl_UniProt_AC"].get("alias")
            )
            s_node[NT.description] = description_table.loc[start].get("annotation")

            nodes_in[start] = s_node[NT.id]
            G.add_node(s_node[NT.id], **s_node)

        if end not in nodes_in:

            e_node[NT.id] = int(next_id)
            next_id += 1
            e_node[NT.name] = end
            # get uniprot id(s)
            alias = alias_table.loc[end]
            e_node["uniprot"] = list(
                alias.loc[alias["source"] == "Ensembl_UniProt_AC"].get("alias").values
            )
            e_node[NT.species] = species
            annotation = description_table.loc[end].get("annotation")
            if annotation != "annotation not available":
                e_node[NT.description] = annotation

            nodes_in[end] = e_node[NT.id]
            G.add_node(e_node[NT.id], **e_node)

        link[LiT.id] = idx
        link[LiT.start] = nodes_in[start]
        link[LiT.end] = nodes_in[end]

        for key in ev_columns:
            value = int(row.get(key))
            if value > 0:
                if key == "experimental":
                    key = Evidences.stringdb_experiments.value
                elif key == "database":
                    key = Evidences.stringdb_databases.value
                else:
                    key = f"stringdb_{key}"
            link[key] = value / 1000

        if Evidences.stringdb_experiments.value in link:
            G.add_edge(link[LiT.start], link[LiT.end])

        for ev in l_lays:
            if ev == "any":
                l_lays[ev].append(link)
            if ev in link:
                l_lays[ev].append(link)
    write_network(organism, G, l_lays)
    return G, l_lays


def write_link_layouts(organism: str, l_lays: dict) -> None:
    """Will write the link layouts to a csv file with the following format:
    start,end,r,g,b,a. File name is: {organism}_{ev}.csv located in projects folder.

    Args:
        organism (str): Organism from which the network originates from.
        l_lays (dict): Dictionary of link layouts with ev as key and list of links as value.
    """
    color_scheme = Evidences.get_default_scheme()
    _directory = os.path.join(st._STATIC_PATH, "csv", "STRING", organism)
    os.makedirs(_directory, exist_ok=True)
    files = []
    for ev in l_lays:
        output = ""
        for l, link in enumerate(l_lays[ev]):
            link: dict
            start = link.get(LiT.start)
            end = link.get(LiT.end)
            color = color_scheme[ev]
            value = link.get(ev)
            if value:
                alpha = int(color[3] * value)
            else:
                alpha = 255
            color = color[:3] + tuple((alpha,))
            color = ",".join([str(c) for c in color])
            output += f"{start},{end},{color}\n"
        file_name = os.path.join(_directory, f"{organism}_{ev}.csv")
        with open(file_name, "w") as f:
            f.write(output)
        files.append(file_name)


def write_node_layout(organism: str, G: nx.Graph, layout: dict) -> None:
    """Will write the node layout to a csv file with the following format:
    x,y,r,g,b,a,name;uniprot_id;description. File name is: {organism}_node.csv located in projects folder.

    Args:
        organism (str): organism from which the network originates from.
        G (nx.Graph): Graph of the network.
        layout (dict): calculated layout of the graph. With the node id as key and the position as value.
    """
    _directory = os.path.join(st._STATIC_PATH, "csv", "STRING", organism)
    os.makedirs(_directory, exist_ok=True)
    output = ""
    for i in range(len(layout)):
        node = G.nodes[i]
        pos = layout[i]
        color = (255, 255, 255)
        pos = ",".join([str(p) for p in pos])
        color += ((255 // 2),)
        color = ",".join([str(c) for c in color])
        attr = f"{node.get(NT.name)};{node.get(NT.uniprot)};{node.get(NT.description)}"
        output += f"{pos},{color},{attr}\n"
    file_name = os.path.join(_directory, f"{organism}_node.csv")
    with open(file_name, "w") as f:
        f.write(output)


def write_network(organism: str, G: nx.Graph, l_lays: dict) -> None:
    """Write the graph to a graphml file. And write the l_lays to a json file.

    Args:
        organism (str): Organism from which the network originates from.
        G (nx.Graph): Graph of the network.
        l_lays (dict): Link layouts with ev as key and list of links as value.
    """
    os.makedirs(os.path.join(st._THIS_EXT, "STRING", organism), exist_ok=True)
    graph = nx.node_link_data(G)
    graph["link_layouts"] = l_lays
    json_str = json.dumps(graph) + "\n"
    json_bytes = json_str.encode("utf-8")
    file_name = os.path.join(st._THIS_EXT, "STRING", organism, "network.json.gzip")
    with gzip.open(file_name, "w") as fout:
        fout.write(json_bytes)


def read_network(organism: str) -> tuple[nx.Graph, dict]:
    """Reads the graphml of the network and a json file with the link layouts.

    Args:
        organism (str): Organism from which the network originates from.

    Returns:
        tuple[nx.Graph, dict]: Graph representing the protein-protein interaction network and a dictionary containing the nodes of the graph.
    """
    file_name = os.path.join(st._THIS_EXT, "STRING", organism, "network.json.gzip")
    with gzip.open(file_name, "r") as fin:
        json_bytes = fin.read()
    json_str = json_bytes.decode("utf-8")

    graph = json.loads(json_str)
    l_lays = graph.pop("link_layouts")
    G = nx.node_link_graph(graph)
    return G, l_lays


def gen_layout(G: nx.Graph) -> dict:
    """Generates a 3D layout for the graph.

    Args:
        G (nx.Graph): Graph to generate layout for.

    Returns:
        dict: Dictionary with node ids as keys and 3D positions as values.
    """
    layout = nx.spring_layout(G, dim=3, k=1.0)
    points = np.array(list(layout.values()))
    points = Layouter.to_positive(points, 3)
    points = Layouter.normalize_values(points, 3)
    # write points to node and add position to node data.
    for i, key in enumerate(layout):
        layout[key] = points[i]
    return layout


def construct_layouts(organism: str) -> None:
    """Constructs the layouts for the network and compress them into a tar file.

    Args:
        organism (str): Organism which should be processed.
    """
    G, l_lays = read_network(organism)
    # layout = gen_layout(G)  # TODO Allow different layouts
    write_link_layouts(organism, l_lays)
    # write_node_layout(organism, G, layout)
    # _directory = os.path.join(st._STATIC_PATH, "csv", "STRING", organism)
    # file_name = os.path.join(st._STATIC_PATH, "csv", "STRING", f"{organism}.tgz")
    # with tarfile.open(file_name, "w:gz") as tar:
    #     tar.add(_directory, arcname=organism)
