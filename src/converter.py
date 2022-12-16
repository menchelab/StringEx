import json
import ntpath
import os

import numpy as np
import pandas as pd

from .classes import LayoutTags as LT
from .classes import LinkTags as LiT
from .classes import NodeTags as NT
from .classes import VRNetzElements as VRNE
from .layouter import Layouter
from .settings import _NETWORKS_PATH, UNIPROT_MAP


class VRNetzConverter:
    """Converts a network from edge/link list to VRNetz format

    Args:
        node_files (list[str]or str): A list of paths or a single csv file(s) containing all nodes.
        link_files (list[str]or str, optional): A list of paths or a single path to csv file(s) that contain links. Defaults to None.
        uniprot_mapping_file (str, optional): Path to a uniprot_mapping file where the identifiers are mapped to uniprot ids . Defaults to None.
        project_name (str, optional): Name of the project to which this should all of that be consolidated. Defaults to None.
    """

    def __init__(
        self,
        node_files: list[str] or str,
        link_files: list[str] or str = None,
        uniprot_mapping_file: str = None,
        project_name: str = None,
    ) -> None:

        # Catch None values
        if uniprot_mapping_file is None:
            uniprot_mapping_file = UNIPROT_MAP
        if project_name is None:
            project_name = "PPI.VrNetz"
        if not project_name.endswith(".VRNetz"):
            project_name += ".VRNetz"
        # initialize values
        if type(node_files) is str:
            self.nodes_files = [node_files]
        else:
            self.nodes_files = node_files
        if type(link_files) is str:
            self.links_files = [link_files]
        else:
            self.links_files = link_files
        self.uniprot_mapping_file = uniprot_mapping_file
        self.project_name = project_name
        self.n_layouts = []
        self.l_layouts = []

    def convert(self) -> None:
        """Construct the VrNetz from the links and nodes csv files"""
        nodes_map = {}
        for node_file in self.nodes_files:
            n_layout = ntpath.basename(node_file).split(".")[0]
            self.n_layouts.append(n_layout)
            nodes_map = self.gen_node_layout(node_file, n_layout, nodes_map)

        nodes = list(nodes_map.values())

        links_map = {}
        for link_file in self.links_files:
            l_layout = ntpath.basename(link_file).split(".")[0]
            self.l_layouts.append(l_layout)
            links_map = self.gen_link_list(link_file, l_layout, links_map)

        links = list(links_map.values())

        vr_netz = {
            VRNE.nodes: nodes,
            VRNE.links: links,
            VRNE.node_layouts: self.n_layouts,
            VRNE.link_layouts: self.l_layouts,
        }

        with open(os.path.join(_NETWORKS_PATH, self.project_name), "w+") as f:
            json.dump(vr_netz, f)

    def gen_node_layout(self, node_file: str, layout: str, nodes_map: dict) -> list:
        """Extract node list from a node csv file.

        Args:
            node_file (str): Path to a csv file containing all nodes
            layout (str): Name of layout.
            nodes_map (dict): Contains all node in the network with node id as key and the node as value.
        Returns:
            list: nodes_map contains all node in the network with node id as key and the node as value.
        """
        uniprot_map = pd.read_csv(self.uniprot_mapping_file, sep=",")
        nodes = pd.read_csv(
            node_file,
            sep=",",
            header=None,
            names=["ppi_id", "x", "y", "z"],
        ).to_dict(orient="records")
        points = []
        for node in nodes:
            points.append((node["x"], node["y"], node["z"]))
            index = uniprot_map.index[
                uniprot_map["NCBI Gene ID(supplied by NCBI)"] == node["ppi_id"]
            ].tolist()
            if len(index) > 0:
                node_label = uniprot_map.loc[
                    index[0], "UniProt ID(supplied by UniProt)"
                ]
            else:
                node_label = "NA"
            node[NT.name] = node_label
            for col in ["x", "y", "z"]:
                del node[col]

        points = np.array(points)
        points = Layouter.to_positive(points, 3)
        points = Layouter.normalize_values(points, 3)

        for i, node in enumerate(nodes):
            node[NT.id] = node["ppi_id"]

            # if Node already contained in another layout, add this layout to the node. If not, add the node to the map
            if node[NT.id] in nodes_map:
                node = nodes_map[node[NT.id]]
            else:

                nodes_map[node[NT.id]] = node

            if NT.layouts not in node:
                node[NT.layouts] = []

            for p, point in enumerate(points[i]):
                if pd.isna(point):  # checks whether the point is NaN
                    points[i][p] = 0.0
            node[NT.layouts].append({LT.name: layout, LT.position: list(points[i])})
            nodes_map[node[NT.id]] = node  # update the node in the map

        return nodes_map

    def gen_link_list(self, link_file: str, layout: str, links_map: dict) -> dict:
        """Extract edge dict from a edge csv file

        Args:
            link_file (str): Path to a csv file containing links.
            layout (str): name of the layout which is processed.
            links_map (dict): Contains all links in the network with link id as key and the link as value.

        Returns:
            dict: links_map contains all links in the network with link id as key and the link as value.
        """
        links = pd.read_csv(link_file, sep=",", header=None, names=["s", "e"]).to_dict(
            orient="records"
        )

        for i, link in enumerate(links):
            link[LiT.id] = i
            if link[LiT.id] in links_map:
                link = links_map[link[LiT.id]]
            else:
                links_map[link[LiT.id]] = link

            if LiT.layouts not in link:
                link[LiT.layouts] = []
            link[LiT.layouts].append({LT.name: layout})

        return links_map


if __name__ == "__main__":
    link_list = "/Users/till/Documents/Playground/PPI_network/elists/PPI_full_elist.csv"
    node_list = "/Users/till/Documents/Playground/PPI_network/layouts/PPI_physical_eigenlayout_3D.csv"
    uniprot_mapping_file = (
        "/Users/till/Documents/Playground/STRING-VRNetzer/static/uniprot_mapping.csv"
    )
    VRNetzConverter(
        link_list,
        node_list,
        uniprot_mapping_file,
    )
