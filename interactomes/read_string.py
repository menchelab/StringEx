import glob
import gzip
import json
import os
import tarfile

import networkx as nx
import numpy as np
import pandas
import requests

from src import map_uniprot
from src import settings as st
from src.classes import Evidences
from src.classes import LinkTags as LiT
from src.classes import NodeTags as NT
from src.classes import Organisms
from src.layouter import Layouter


def construct_graph(
    networks_directory: str, organism: str, clean_name, last_link: int or None = None
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
    directory = os.path.join(networks_directory, clean_name)
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
    return gen_graph(network_table, alias_table, description_table, organism, clean_name, networks_directory, last_link)


def gen_graph(
    network_table: pandas.DataFrame,
    alias_table: pandas.DataFrame,
    description_table: pandas.DataFrame,
    organism: str,
    clean_name: str,
    _dir:str, 
    last_link: int or None = None,
    threshold: int=0,
) -> tuple[nx.Graph, dict]:
    """Extracts data from the STRING database files and constructs a graph representing the protein-protein interaction network.

    Args:
        network_table (pandas.DataFrame): Data Frame containing all links of the network.
        alias_table (pandas.DataFrametr): Data Frame containing all aliases of the proteins.
        description_table (pandas.DataFrame): Data Frame containing Descriptions of the proteins.
        organism (str): Organism from which the network originates from.
        last_link (int or None, optional): FOR DEBUGGING: Integer of the last link to be processed. Defaults to None.
        threshold (int): Score threshold, every edge having an experimental score larger than this value is used for layout calculation. Defaults to 0.

    Returns:
        tuple[nx.Graph, dict]: Graph representing the protein-protein interaction network and a dictionary containing the nodes of the graph.
    """

    species = Organisms.get_scientific_name(organism)
    taxid = Organisms.get_tax_ids(organism)
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
    all_links = []
    map_gene_name = {}
    
    def extract_unirot_id(alias:pandas.DataFrame) -> list:
        """Extracts possible uniprot ids from the alias column of a node.

        Args:
            alias (pd.DataFrame): Dataframe containing only data for a single node.

        Returns:
            list: contains all uniprot ids for a node.
        """
        for tag in ["Ensembl_UniProt_AC", "BLAST_UniProt_AC"]:
            uniprot = list(
                        alias.loc[alias["source"] == tag].get("alias")
                    )
            if len(uniprot)>0:
                return uniprot[0]
        return None

    def extract_gene_name(alias:pandas.DataFrame):
        """Extracts possible gene names from the alias column of a node.

        Args:
            alias (pd.DataFrame): Dataframe containing only data for a single node.

        Returns:
            list: contains all gene names for a node.
        """
        gene_name = list(
            alias.loc[alias["source"] == "BLAST_UniProt_GN_Name"].get("alias")
        )
        if len(gene_name) == 0:
            return None
        
        return gene_name[0]

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
            uniprot = extract_unirot_id(alias)
            if uniprot:
                s_node["uniprot"] = uniprot

            gene_name = extract_gene_name(alias)
            if gene_name:
                s_node[NT.name] = gene_name
                if not uniprot:
                    map_gene_name[e_node[NT.id]] = gene_name
                
            s_node[NT.description] = description_table.loc[start].get("annotation")
            nodes_in[start] = s_node[NT.id]
            G.add_node(s_node[NT.id], **s_node)

        if end not in nodes_in:

            e_node[NT.id] = int(next_id)
            next_id += 1
            e_node[NT.name] = end
            # get uniprot id(s)
            alias = alias_table.loc[end]
            uniprot = extract_unirot_id(alias)
            if uniprot:
                e_node["uniprot"] = uniprot
            gene_name = extract_gene_name(alias)
            if gene_name:
                e_node[NT.name] = gene_name
                if not uniprot:
                    map_gene_name[e_node[NT.id]] = gene_name
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

        # Only add experimental proven edges for layout calculation
        if Evidences.stringdb_experiments.value in link:
            if link.get(Evidences.stringdb_experiments.value) > threshold:
                G.add_edge(link[LiT.start], link[LiT.end])

        all_links.append(link)

        # Add all edges the their respective ev list for link layouts.
        for ev in l_lays:
            if ev == "any":
                l_lays[ev].append(idx)
            if ev in link:
                l_lays[ev].append(idx)

    # Map gene names to uniprot ids and add them to the nodes.
    G = map_gene_names_to_uniprot(G, map_gene_name,taxid)

    graph_data = nx.node_link_data(G)
    graph_data["link_layouts"] = l_lays
    graph_data["all_links"] = all_links
    write_network(clean_name, graph_data, _dir)

    st.log.info(f"Network for {organism} has {len(G.nodes)} nodes and {len(G.edges)} edges.")

    return G, l_lays

def map_gene_names_to_uniprot(G:nx.Graph,map_gene_name:dict,taxid:str) -> nx.Graph:
    """Maps gene names to uniprot ids and adds them to the nodes.

    Args:
        G (nx.Graph): Graph Containing all nodes of the network.
        map_gene_name (dict): dict that maps node ids to gene names.
        taxid (str): taxonomic id of the organism.

    Returns:
        nx.Graph: Same graph as the input graph, but with updated uniprot ids.
    """    
    if len(map_gene_name) > 0:
        st.log.debug("Mapping gene names to uniprot ids...")
        invert_map = {v:k for k,v in map_gene_name.items()}

        query_results= map_uniprot.query_gen_names_uniport(taxid,list(map_gene_name.values()))
        with open("test.json", "w") as f:
            json.dump(query_results, f)
        for entry in query_results["results"]:
            gene_name = entry.get("from")
            primaryAccession = None

            if isinstance(entry["to"], dict):
                references = entry["to"].get("uniProtKBCrossReferences")
                for ref in references:
                    if ref.get("database") == "AlphaFoldDB":
                        primaryAccession = ref.get("id")
                        break
                if not primaryAccession:
                    primaryAccession = entry["to"].get("primaryAccession")
            else:
                primaryAccession = entry["to"]
                
            G.nodes[invert_map[gene_name]]["uniprot"] = primaryAccession

    return G

def write_link_layouts(organism: str, l_lays: dict, all_links:list, _dir:str) -> None:
    """Will write the link layouts to a csv file with the following format:
    start,end,r,g,b,a. File name is: {organism}_{ev}.csv located in projects folder.

    Args:
        organism (str): Organism from which the network originates from.
        l_lays (dict): Dictionary of link layouts with ev as key and list of links as value.
        all_links (list): contains all links in the network, predicted and experimental proven.
        dir (str): Directory to write the files to.
    """
    color_scheme = Evidences.get_default_scheme()
    _directory = os.path.join(_dir, organism)
    os.makedirs(_directory, exist_ok=True)
    files = []
    for ev in l_lays:
        output = ""
        for l, idx in enumerate(l_lays[ev]):
            link = all_links[idx]
            start = link.get(LiT.start)
            end = link.get(LiT.end)
            color = color_scheme[ev]

            if ev in link:
                alpha = int(color[3] * link.get(ev))
            else:
                alpha = 255

            color = color[:3] + tuple((alpha,))
            color = ",".join([str(c) for c in color])
            output += f"{start},{end},{color}\n"
        file_name = os.path.join(_directory, f"{ev}.csv")
        with open(file_name, "w") as f:
            f.write(output)
        files.append(file_name)
        st.log.info(f"link layout for evidence {ev} for {organism} has been written to {file_name}.")


def write_node_layout(organism: str, G: nx.Graph, layout: dict, _dir:str) -> None:
    """Will write the node layout to a csv file with the following format:
    x,y,r,g,b,a,name;uniprot_id;description. File name is: {organism}_node.csv located in projects folder.

    Args:
        organism (str): organism from which the network originates from.
        G (nx.Graph): Graph of the network.
        layout (dict): calculated layout of the graph. With the node id as key and the position as value.
    """
    _directory = os.path.join(_dir, organism)
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
    file_name = os.path.join(_directory, f"nodes.csv")
    with open(file_name, "w") as f:
        f.write(output)
    st.log.info(f"Node layout for {organism} has been written to {file_name}.")


def write_network(organism: str, graph: dict,_dir:str) -> None:
    """Write the graph to a json file. And write the l_lays to a json file.

    Args:
        organism (str): Organism from which the network originates from.
        G (nx.Graph): Graph of the network.
        l_lays (dict): Link layouts with ev as key and list of links as value.
    """
    os.makedirs(os.path.join(_dir, organism), exist_ok=True)
    json_str = json.dumps(graph) + "\n"
    json_bytes = json_str.encode("utf-8")
    file_name = os.path.join(_dir, organism, "network.json.gzip")
    with gzip.open(file_name, "w") as fout:
        fout.write(json_bytes)


def read_network(organism: str, _dir:str) -> tuple[nx.Graph, dict]:
    """Reads the graphml of the network and a json file with the link layouts.

    Args:
        organism (str): Organism from which the network originates from.

    Returns:
        tuple[nx.Graph, dict]: Graph representing the protein-protein interaction network and a dictionary containing the nodes of the graph.
    """
    file_name = os.path.join(_dir,  organism, "network.json.gzip")
    with gzip.open(file_name, "r") as fin:
        json_bytes = fin.read()
    json_str = json_bytes.decode("utf-8")

    graph = json.loads(json_str)
    l_lays = graph.pop("link_layouts")
    all_links = graph.pop("all_links")
    G = nx.node_link_graph(graph)
    st.log.info(f"Read network from file {file_name}.")
    return G, l_lays, all_links


def gen_layout(G: nx.Graph, layout_algo:str = None, variables:dict=None) -> dict:
    """Generates a 3D layout for the graph.

    Args:
        G (nx.Graph): Graph to generate layout for.

    Returns:
        dict: Dictionary with node ids as keys and 3D positions as values.
    """
    layouter = Layouter()
    layouter.graph = G
    layout = layouter.apply_layout(layout_algo, variables)
    points = np.array(list(layout.values()))
    points = Layouter.to_positive(points, 3)
    points = Layouter.normalize_values(points, 3)
    # write points to node and add position to node data.
    for i, key in enumerate(layout):
        layout[key] = points[i]
    st.log.info(f"Generated layout. Used algorithm: {layout_algo}.")
    return layout

def construct_layouts(organism: str, _dir:str,layout_algo:str=None,variables:dict=None) -> None:
    """Constructs the layouts for the network and compress them into a tar file.

    Args:
        organism (str): Organism which should be processed.
        _dir (str): Path to the directory in which all files are saved in.
        layout_algo (str): Defines the layout algorithm which should be used.
        variables (dict): Defines the variables of the respective layout algorithm.
    """
    G, l_lays, all_links = read_network(organism, _dir)
    layout = gen_layout(G, layout_algo, variables)
    write_link_layouts(organism, l_lays, all_links, _dir)
    write_node_layout(organism, G, layout ,_dir)
    file_name = os.path.join(_dir, f"{organism}.tgz")
    organism_dir = os.path.join(_dir, organism)
    with tarfile.open(file_name, "w:gz") as tar:
        tar.add(organism_dir, arcname=organism)
    st.log.info(f"Compressed layouts to {file_name}.")