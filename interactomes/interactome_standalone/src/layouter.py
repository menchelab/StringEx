import json
import random

import networkx as nx
import numpy as np

# from . import util
from .classes import Evidences
from .classes import LayoutAlgroithms as LA
from .classes import LayoutTags as LT
from .classes import LinkTags as LiT
from .classes import NodeTags as NT
from .classes import StringTags as ST
from .classes import VRNetzElements as VRNE
from .logger import log


class Layouter:
    """Simple class to apply a 3D layout algorithm to a networkx graph.

    """
    graph: nx.Graph = nx.Graph()

    def gen_graph(self, nodes: dict, links: dict) -> nx.Graph:
        """Generates a networkx graph based on a dict of nodes and links.

        Args:
            nodes (dict): contains all nodes that should be part of the graph with node ids as keys and nodes as values.
            links (dict): contains all links that should be part of the graph with link ids as keys and links as values.

        Returns:
            networkx.Graph: Graph for which the layouts will be generated.
        """
        for node_data in nodes:
            self.graph.add_node(node_data[NT.id], data=node_data)
            # self.node_map[node_data["id"]] = node_data
        for link in links:
            self.graph.add_edge(link[LiT.start], link[LiT.end], data=link)
            # self.edge_map[(str(edge["s"]), str(edge["e"]))] = edge
        self.network = {VRNE.nodes: nodes, VRNE.links: links}
        return self.graph

    def read_from_vrnetz(self, file: str) -> nx.Graph:
        """Reads a graph from a VRNetz file.

        Args:
            file (str): Path to a VRNetz file.

        Returns:
            networkx.Graph: Graph for which the layouts will be generated.
        """
        network = json.load(open(file))
        self.network = network
        nodes = network[VRNE.nodes]
        links = network[VRNE.links]
        return self.gen_graph(nodes, links)

    def get_node_data(self, node: str) -> dict:
        """Get the data of the desired node.

        Args:
            node (str): id of the desired node.

        Returns:
            dict: containing all data of a node
        """
        if "data" not in self.graph.nodes[node]:
            self.graph.nodes[node]["data"] = {}
        # self.graph.nodes[node].get("data",{}) # might work not sure
        return self.graph.nodes[node]["data"]

    def set_node_data(self, node: str, data: dict) -> None:
        """Set the dat of a desired node.

        Args:
            node (str):  id of the desired node.
            data (dict): containing all data of a node
        """
        self.graph.nodes[node]["data"] = data

    def read_from_grahpml(self, file: str) -> nx.Graph:
        """Read a graph from a graphml file.

        Args:
            file (str): path to the graphml file.

        Returns:
            networkx.Graph: Graph for which the layouts will be generated.
        """
        self.graph = nx.read_graphml(file)
        return self.graph

    def create_spring_layout(self, algo_variables: dict) -> dict:
        """Generates a spring layout for the Graph.

        Args:
            algo_variables (dict): contains variables for the algorithm.

        Returns:
            dict: node ids as keys and three dimensional positions as values.
        """
        k = algo_variables.get("opt_dist")
        iterations = algo_variables.get("iterations", 50)
        threshold = algo_variables.get("threshold", 0.0001)
        return nx.spring_layout(
            self.graph, dim=3, k=k, iterations=iterations, threshold=threshold
        )

    def create_kamada_kawai_layout(self, algo_variables: dict) -> dict:
        """Generates a kamada kawai layout for the Graph.
        Args:
            algo_variables (dict): contains variables for the algorithm. Does not do anything.
        Returns:
            dict: node ids as keys and three dimensional positions as values.
        """
        return nx.kamada_kawai_layout(self.graph, dim=3)

    def create_cartoGRAPH_layout(
        self, layout_algo: str, cg_variables: dict = None
    ) -> dict:
        """Will pick the correct cartoGRAPHs layout algorithm and apply it to the graph. If cartoGRAPH is not installed an ImportError is raised.

        Args:
            layout_algo (str): layout algorithm to choose. possible algorithms are listed in setting.LayoutAlgroithms.
            cg_variables (dict, optional): contains algorithm variables. Defaults to None.

        Returns:
            dict: node ids as keys and three dimensional positions as values.
        """
        # try:
        import cartoGRAPHs as cg

        dim = 3

        if "tsne" in layout_algo:
            prplxty = cg_variables.get("prplxty", 50)
            density = cg_variables.get("density", 0.5)
            l_rate = cg_variables.get("l_rate", 200)
            steps = cg_variables.get("steps", 250)
            if "local" in layout_algo:
                return cg.layout_local_tsne(
                    self.graph, dim, prplxty, density, l_rate, steps
                )
            elif "global" in layout_algo:
                return cg.layout_global_tsne(
                    self.graph, dim, prplxty, density, l_rate, steps
                )
            elif "importance" in layout_algo:
                return cg.layout_importance_tsne(
                    self.graph, dim, prplxty, density, l_rate, steps
                )
            elif "functional" in layout_algo:
                return cg.layout_functional_tsne(
                    self.graph, dim, prplxty, density, l_rate, steps
                )
        if "umap" in layout_algo:
            n_neighbors = cg_variables.get("n_neighbors", 10)
            spread = cg_variables.get("spread", 1.0)
            min_dist = cg_variables.get("min_dist", 0.1)
            if "local" in layout_algo:
                return cg.layout_local_umap(
                    self.graph, dim, n_neighbors, spread, min_dist
                )
            elif "global" in layout_algo:
                return cg.layout_global_umap(
                    self.graph, dim, n_neighbors, spread, min_dist
                )
            elif "importance" in layout_algo:
                return cg.layout_importance_umap(
                    self.graph, dim, n_neighbors, spread, min_dist
                )
            elif "functional" in layout_algo:
                "TODO: Implement functional"
                MATRIX = cg.get_functional_matrix(self.graph)
                rows = len(list(G.nodes()))
                feat_one = [(val) if i % 3 else (scale) for i in range(rows)]
                feat_two = [
                    (val) if i % 2 or feat_one[i] == scale in feat_one else (scale)
                    for i in range(rows)
                ]
                feat_three = [
                    (scale)
                    if feat_one[i] == val
                    and feat_two[i] == val
                    and i not in feat_one
                    and i not in feat_two
                    else val
                    for i in range(rows)
                ]

                feat_matrix = np.vstack((feat_one, feat_two, feat_three))
                FM = pd.DataFrame(feat_matrix)
                FM.index = ["100", "101", "102"]
                FM = FM.T
                FM.index = list(G.nodes())
                "Please specify a functional matrix of choice with N x rows with G.nodes and M x feature columns."
                return cg.layout_functional_umap(
                    self.graph, dim, n_neighbors, spread, min_dist
                )
        elif "topographic" in layout_algo:
            # d_z = a dictionary with keys=G.nodes and values=any int/float assigned to a node
            posG2D = nx.Graph()
            z_list = [np.random.random() for i in range(0, len(list(posG2D.nodes())))]
            d_z = dict(zip(list(posG2D.nodes()), z_list))
            return cg.layout_topographic(posG2D, d_z)

        elif "geodesic" in layout_algo:
            d_radius = 1
            n_neighbors = 8
            spraed = 1.0
            min_dist = 0.0
            DM = None
            # radius_list_norm = preprocessing.minmax_scale((list(d_radius.values())), feature_range=(0, 1.0), axis=0, copy=True)
            # d_radius_norm = dict(zip(list(G.nodes()), radius_list_norm))
            return cg.layout_geodesic(
                self.graph, d_radius, n_neighbors, spread, min_dist, DM
            )
        # except ImportError:
        #     log.warning("cartoGRAPHs is not installed.")
        #     use_spring = input("Use spring layout instead? [y/n]: ")
        #     if use_spring == "y":
        #         return self.create_spring_layout()
        #     else:
        #         exit()

    def apply_layout(
        self, layout_algo: str = None, algo_variables: dict = {}
    ) -> dict[str, list[float]]:
        """Applies a layout algorithm and adds the node positions to nodes in the self.network[VRNE.nodes] list.

        Args:
            layout_algo (str, optional): layout algorithm to choose. possible algorithms are listed in setting.LayoutAlgroithms.. Defaults to None.
            algo_variables (dict, optional): Contains algorithm variables. Defaults to None.. Defaults to {}.

        Returns:
            dict[str,list[float]]: with node ids as keys and three dimensional node positions as values.
        """
        if layout_algo is None:
            """Select default layout algorithm"""
            layout_algo = LA.spring

        if LA.cartoGRAPH in layout_algo:
            layout = self.create_cartoGRAPH_layout(layout_algo, algo_variables)
        else:
            layouts = {
                LA.spring: self.create_spring_layout,
                LA.kamada_kawai: self.create_kamada_kawai_layout,
            }
            log.debug(f"Applying layout: {layout_algo}")
            layout = layouts[layout_algo](
                algo_variables
            )  # Will use the desired layout algorithm

        points = np.array(list(layout.values()))
        points = self.to_positive(points, 3)
        points = self.normalize_values(points, 3)

        # write points to node and add position to node data.
        for i, key in enumerate(layout):
            layout[key] = points[i]

        return layout

    def add_layout_to_vrnetz(self,layout:dict) -> None:
        """Adds the points of the generated layout to the underlying VRNetz

        Args:
            layout (dict): Dictionary containing node ids as keys and a 3-tuple of coordinates as values.
        """
        if VRNE.node_layouts not in self.network:
                self.network[VRNE.node_layouts] = []
                
        if LT.string_3d_no_z not in self.network[VRNE.node_layouts]:
            self.network[VRNE.node_layouts].append(LT.string_3d_no_z)

        if LT.string_3d not in self.network[VRNE.node_layouts]:
            self.network[VRNE.node_layouts].append(LT.string_3d)

        idx = 0
        cytoscape_nodes = []
        cy_points = []
        log.debug(f"Length of Layout {len(layout)}")
        for node, pos in layout.items():
            node = self.network[VRNE.nodes][idx]
            color = [
                random.randint(0, 255),
                random.randint(0, 255),
                random.randint(0, 255),
            ]
            size = 1
            # find the correct layout
            cy_layout, layout_id = util.find_cy_layout(node)
            if cy_layout:
                cytoscape_nodes.append(node)
                cy_pos = node[NT.layouts][layout_id][LT.position]
                cy_points.append(cy_pos)
                # extract color and (size) information
                size = cy_layout[LT.size]
                color = cy_layout[LT.color]
                node[NT.layouts][layout_id][LT.color] = color

            if NT.layouts not in node:
                node[NT.layouts] = []

            node[NT.layouts].append(
                {
                    LT.name: LT.string_3d_no_z,
                    LT.position: (pos[0], pos[1], 0.0),
                    LT.color: color,
                    LT.size: size,
                }
            )  # Add 2D coordinates

            node[NT.layouts].append(
                {
                    LT.name: LT.string_3d,
                    LT.position: tuple(pos),
                    LT.color: color,
                    LT.size: size,
                }
            )  # Add 3D coordinates

            self.network[VRNE.nodes][idx] = node

            idx += 1

        self.correct_cytoscape_pos(cytoscape_nodes, cy_points, layout_id)

    def correct_cytoscape_pos(
        self, cytoscape_nodes: list, points: list[list[float]], layout_id: int
    ) -> np.array:
        """Corrects the Cytoscape positions to be positive and between 0 and 1.

        Args:
            cytoscape_nodes (list): list of nodes that are part of the cytoscape layout
            points (list[list[float]]): 2d array that contains all positions for every node.
            layout_id (int): id of the layout in each node dictionary.

        Returns:
            np.array: 2d Array contains all positions for every node but now normalized between 0 and 1.
        """

        if len(points) == 0:
            return None
        # normalize positions between in [0,1]
        points = np.array(points)
        points = self.to_positive(points, 2)
        points = self.normalize_values(points, 2)

        # Write new formatted node positions on the xz axis
        for node, position in zip(cytoscape_nodes, points):
            node[NT.layouts][layout_id][LT.position] = tuple(
                (position[0], position[1], 0.0)
            )
            self.network[VRNE.nodes][node[NT.id]] = node  # Update node data

        return points

    @staticmethod
    def to_positive(points: np.array, dims=3) -> np.array:
        """Move every coordinate to positive space.

        Args:
            points (np.array):  2d array that contains all positions for every node.
            dims (int, optional): Dimensions each node point has. Defaults to 3.

        Returns:
            np.array: 2d array that contains all positions for every node with only positive values.
        """
        min_values = [min(points[:, i]) for i in range(dims)]
        # Move everything into positive space
        for i, point in enumerate(points):
            for d, _ in enumerate(point[:dims]):
                points[i, d] += abs(min_values[d])
        return points

    @staticmethod
    def normalize_values(points, dims=3) -> np.array:
        """Scale every coordinate between 0 and 1

        Args:
            points (np.array):  2d array that contains all positions for every node.
            dims (int, optional): Dimensions each node point has. Defaults to 3.

        Returns:
            np.array: 2d array that contains all positions for every node with values only between 0 and 1
        """
        # Normalize Values between 0 and 1
        min_values = [min(points[:, i]) for i in range(dims)]
        max_values = [max(points[:, i]) for i in range(dims)]
        norms = [max_values[i] - min_values[i] for i in range(dims)]
        for i, point in enumerate(points):
            for d, _ in enumerate(point[:dims]):
                points[i, d] /= norms[d]
        return points

    def gen_evidence_layouts(
        self, evidences: dict[str, tuple[float, float, float, float]] or None = None
    ) -> list[dict[str, object]]:
        """Set the link color for each STRING evidence type. Based on the score the link opacity is scaled.

        Args:
            evidences (dict[str, tuple[float, float, float, float]] or None, optional): Contains all possible evidence types and their corresponding color. Defaults to None.

        Returns:
            list: list of link dictionaries.
        """
        # Set up the colors for each evidence type
        if evidences is None:
            evidences = Evidences.get_default_scheme()
        log.debug(f"Evidence colors: {evidences}")
        links = self.network[VRNE.links]
        log.debug(f"links loaded.")
        if VRNE.link_layouts not in self.network:
            self.network[VRNE.link_layouts] = []
        for ev in evidences:
            log.debug(f"Handling evidence: {ev}.")
            self.network[VRNE.link_layouts].append(ev)
            if not ev == Evidences.any.value:
                cur_links = {idx: link for idx, link in enumerate(links) if ev in link}
            else:
                cur_links = {idx: link for idx, link in enumerate(links)}
            # Skip This evidence if there are not edges for this evidence
            if len(cur_links) == 0:
                continue

            # Color each link with the color of the evidence
            for idx, link in cur_links.items():
                scale_factor = 0
                if ev == Evidences.any.value:
                    scale_factor = link.get(ST.stringdb_score)
                    if not scale_factor:
                        scale_factor = 0
                        for other_ev in [
                            e.value for e in Evidences if e != Evidences.any
                        ]:
                            if other_ev in link:
                                if link[other_ev] > scale_factor:
                                    scale_factor = link[other_ev]
                else:
                    scale_factor = link[ev]
                color = evidences[ev][:3] + (
                    int(scale_factor * 255),
                )  # Alpha scales with score
                if LiT.layouts not in self.network[VRNE.links][idx]:
                    self.network[VRNE.links][idx][LiT.layouts] = []
                self.network[VRNE.links][idx][LiT.layouts].append(
                    {LT.name: ev, LT.color: color}
                )
        return self.network[VRNE.links]


if __name__ == "__main__":
    import os

    layouter = Layouter()
    layouter.read_from_vrnetz(
        os.path.abspath(
            f"{__file__}/../../static/networks/STRING_network_-_Alzheimer's_disease.VRNetz"
        )
    )
    layouter.apply_layout()
