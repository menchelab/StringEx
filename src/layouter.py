import json
import os
from multiprocessing import Pool

import matplotlib.pyplot as plt
import networkx as nx
import numpy as np
import pandas as pd
import swifter

from . import util
from .classes import Evidences
from .classes import LayoutAlgorithms as LA
from .classes import LayoutTags as LT
from .classes import LinkTags as LiT
from .classes import NodeTags as NT
from .classes import StringTags as ST
from .classes import VRNetzElements as VRNE
from .settings import log


class Layouter:
    """Simple class to apply a 3D layout algorithm to a networkx graph."""

    graph: nx.Graph = nx.Graph()

    @staticmethod
    def gen_graph(nodes: dict = None, links: dict = None) -> nx.Graph:
        """Generates a networkx graph based on a dict of nodes and links.

        Args:
            nodes (dict): contains all nodes that should be part of the graph with node ids as keys and nodes as values.
            links (dict): contains all links that should be part of the graph with link ids as keys and links as values.

        Returns:
            networkx.Graph: Graph for which the layouts will be generated.
        """
        G = nx.Graph()
        G.add_nodes_from([(idx, node.dropna()) for idx, node in nodes.iterrows()])
        G.add_edges_from(
            [(start, end) for start, end in links[[LiT.start, LiT.end]].values.tolist()]
        )
        return G

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

    def create_spring_layout(self, algo_variables: dict, random_lay: bool) -> dict:
        """Generates a spring layout for the Graph using the networkx spring_layout algorithm. All nodes without a link will be placed on a sphere around the center of the graph.

        Args:
            algo_variables (dict): contains variables for the algorithm.

        Returns:
            dict: node ids as keys and three dimensional positions as values.
        """
        k = algo_variables.get("opt_dist")
        if k is not None:
            if k <= 0:
                k = None
        iterations = algo_variables.get("iterations", 50)
        threshold = algo_variables.get("threshold", 0.0001)
        algo_variables = {
            "k": k,
            "iterations": iterations,
            "threshold": threshold,
        }
        return self.link_based_layout(nx.spring_layout, algo_variables, random_lay)
        if random_lay:
            return self.create_random_layout()
        return nx.spring_layout(
            self.graph, dim=3, k=k, iterations=iterations, threshold=threshold
        )

    def create_kamada_kawai_layout(self, algo_variables: dict, random_lay) -> dict:
        """Generates a kamada kawai layout for the Graph using the networkx kamada_kawai_layout algorithm. All nodes without a link will be placed on a sphere around the center of the graph.

        Args:
            algo_variables (dict): contains variables for the algorithm. Does not do anything.
        Returns:
            dict: node ids as keys and three dimensional positions as values.
        """
        return self.link_based_layout(
            nx.kamada_kawai_layout, algo_variables, random_lay
        )
        if random_lay:
            return self.create_random_layout()
        return nx.kamada_kawai_layout(self.graph, dim=3)

    def create_random_layout(self, graph=None, algo_variables: dict = {}) -> dict:
        """Generates a random layout for the Graph using the networkx random_layout algorithm.

        Args:
            algo_variables (dict): contains variables for the algorithm. Does not do anything.
        Returns:
            dict: node ids as keys and three dimensional positions as values.
        """
        if graph is None:
            graph = self.graph
        return nx.random_layout(graph, dim=3)

    def create_cartoGRAPH_layout(
        self,
        layout_algo: str,
        cg_variables: dict = None,
        feature_matrix: pd.DataFrame = None,
        max_num_features: int = None,
        random=False,
    ) -> dict:
        """Will pick the correct cartoGRAPHs layout algorithm and apply it to the graph. If cartoGRAPH is not installed an ImportError is raised. In link based algorithms all nodes without a link will be placed on a sphere around the center of the graph. In functional algorithms all nodes without a feature will be placed on a sphere around the center of the graph.

        Args:
            layout_algo (str): layout algorithm to choose. possible algorithms are listed in setting.LayoutAlgroithms.
            cg_variables (dict, optional): contains algorithm variables. Defaults to None.

        Raises:
            ImportError: If cartoGRAPHs is not installed.
            NotImplementedError: If the chosen algorithm is not implemented yet ("topographic" and "geodesic")

        Returns:
            dict: node ids as keys and three dimensional positions as values.
        """
        import cartoGRAPHs as cg

        dim = 3
        if "functional" in layout_algo:
            features = feature_matrix.any(axis=1)
            no_feature_index = feature_matrix[~features].copy().index

            feature_matrix = feature_matrix[
                features
            ]  # Filtered feature matrix with out nodes without features

            feature_graph = self.graph.subgraph(feature_matrix.index)
            sphere_graph = self.graph.subgraph(no_feature_index)

        if "tsne" in layout_algo:
            algo_variables = {
                "prplxty": cg_variables.get("prplxty", 50),
                "density": cg_variables.get("density", 12),
                "l_rate": cg_variables.get("l_rate", 200),
                "steps": cg_variables.get("steps", 250),
            }
            if "local" in layout_algo:
                function = cg.layout_local_tsne
            elif "global" in layout_algo:
                function = cg.layout_global_tsne
            elif "importance" in layout_algo:
                function = cg.layout_importance_tsne
            elif "functional" in layout_algo:
                if feature_matrix is None:
                    return ValueError("No feature matrix given.")
                if random:
                    functional = self.create_random_layout(feature_graph)
                else:
                    functional = cg.layout_functional_tsne(
                        feature_graph, feature_matrix, dim, **algo_variables
                    )
                layout = sample_sphere(sphere_graph, list(functional.values()))
                functional.update(layout)
                return functional
        elif "umap" in layout_algo:
            algo_variables = {
                "n_neighbors": cg_variables.get("n_neighbors", 10),
                "spread": cg_variables.get("spread", 1.0),
                "min_dist": cg_variables.get("min_dist", 0.1),
            }
            if "local" in layout_algo:
                function = cg.layout_local_umap
            elif "global" in layout_algo:
                function = cg.layout_global_umap
            elif "importance" in layout_algo:
                function = cg.layout_importance_umap
            elif "functional" in layout_algo:
                if feature_matrix is None:
                    return ValueError("No feature matrix given.")
                if random:
                    functional = self.create_random_layout(feature_graph)
                else:
                    log.debug("Gen functional layout")
                    functional = cg.layout_functional_umap(
                        feature_graph,
                        feature_matrix,
                        dim,
                        **algo_variables,
                    )
                layout = sample_sphere(sphere_graph, list(functional.values()))
                functional.update(layout)
                return functional

        elif "topographic" in layout_algo:
            raise NotImplementedError("Topographic layout not implemented yet!")
            # d_z = a dictionary with keys=G.nodes and values=any int/float assigned to a node
            posG2D = nx.Graph()
            z_list = [np.random.random() for i in range(0, len(list(posG2D.nodes())))]
            d_z = dict(zip(list(posG2D.nodes()), z_list))
            return cg.layout_topographic(posG2D, d_z)

        elif "geodesic" in layout_algo:
            raise NotImplementedError("Geodesic layout not implemented yet!")
            d_radius = 1
            n_neighbors = 8
            spread = 1.0
            min_dist = 0.0
            DM = None
            # radius_list_norm = preprocessing.minmax_scale((list(d_radius.values())), feature_range=(0, 1.0), axis=0, copy=True)
            # d_radius_norm = dict(zip(list(G.nodes()), radius_list_norm))
            return cg.layout_geodesic(
                self.graph, d_radius, n_neighbors, spread, min_dist, DM
            )

        return self.link_based_layout(function, algo_variables, random)

    def link_based_layout(
        self, layout_algo, algo_variables: dict, random_lay: bool, G: nx.Graph = None
    ) -> dict[str, list[float, float, float]]:
        """Will apply a link based layout algorithm to the graph. All nodes with degree 0 will be placed on a sphere around the graph.

        Args:
            layout_algo (Callable): Layout function to apply.
            algo_variables (dict): dict with algorithm variables.
            random_lay (bool): If True, a random layout will be applied.
            G (networkx, optional): . Defaults to None. If None, self.graph will be used.

        Returns:
            dict[str,list[float,float,float]]: node ids as keys and three dimensional positions as values.
        """
        if G is None:
            G = self.graph

        no_links = G.subgraph([n for n, d in G.degree() if d == 0])
        has_links = G.subgraph([n for n in G.nodes() if n not in no_links.nodes()])
        log.debug(
            f"#Nodes with links: {len(has_links.nodes)}, #Nodes without links: {len(no_links.nodes)}"
        )
        log.debug(f"Algo variables:{algo_variables}")

        # # No Sphere
        # has_links = G
        # no_links = []

        if random_lay:
            layout = self.create_random_layout(has_links)
        else:
            layout = layout_algo(has_links, **algo_variables, dim=3)

        if len(no_links) > 0:
            no_links_layout = sample_sphere(no_links, list(layout.values()))
            layout.update(no_links_layout)
        return layout

    def apply_layout(
        self,
        layout_algo: str = None,
        algo_variables: dict = {},
        feature_matrices: list[pd.DataFrame] = None,
        max_num_features: int = None,
        random_lay=False,
    ) -> dict[str, list[float, float, float]]:
        """Applies a layout algorithm and adds the node positions to nodes in the self.network[VRNE.nodes] list.

        Args:
            layout_algo (str, optional): layout algorithm to choose. possible algorithms are listed in setting.LayoutAlgroithms.. Defaults to None.
            algo_variables (dict, optional): Contains algorithm variables. Defaults to None.. Defaults to {}.

        Returns:
            dict[str,list[float,float,float]]: with node ids as keys and three dimensional node positions as values.
        """
        layouts = {}
        if isinstance(layout_algo, str):
            layout_algo = [layout_algo]
        for idx, algo in enumerate(layout_algo):
            if algo is None:
                """Select default layout algorithm"""
                algo = LA.spring
            if LA.cartoGRAPH in algo:
                log.debug(f"Applying layout: {algo}.", flush=True)
                if feature_matrices is None:
                    layout = self.create_cartoGRAPH_layout(
                        algo, algo_variables, random_lay
                    )
                else:
                    layout = self.create_cartoGRAPH_layout(
                        algo,
                        algo_variables,
                        feature_matrices[idx],
                        max_num_features,
                        random_lay,
                    )

                if isinstance(layout, ValueError):
                    log.error(
                        "Error in executing cartoGRAPHs layout. Create a layout with spring instead."
                    )
                    layout = self.create_spring_layout(algo_variables)
            else:
                lay_func = {
                    LA.spring: self.create_spring_layout,
                    LA.kamada_kawai: self.create_kamada_kawai_layout,
                    LA.random: self.create_random_layout,
                }
                log.debug(f"Applying layout: {algo}", flush=True)
                layout = lay_func[algo](
                    algo_variables, random_lay
                )  # Will use the desired layout algorithm
            layouts[idx] = self.normalize_pos(layout)
        return layouts

    @staticmethod
    def normalize_pos(
        layout: dict[int, np.array], dim: int = 3
    ) -> dict[str, list[float, float, float]]:
        """
        Normalizes the positions of the nodes in the layout to be between 0 and 1.

        Args:
            layout (dict[int, np.array]): Dictionary containing node ids as keys and a 3-tuple of coordinates as values.
            dim (int, optional): Defines the dimension in which the coordinates are. Defaults to 3.

        Returns:
            dict[str,list[float,float,float]]: Dictionary containing node ids as keys and a 3-tuple of coordinates as values. Now normalized in the range of 0 to 1.
        """
        layout = dict(sorted(layout.items(), key=lambda x: x[0]))
        pos = np.array(list(layout.values()))
        for i in range(0, dim):
            pos[:, i] += abs(min(pos[:, i]))
            pos[:, i] /= max(pos[:, i])
        layout = dict(zip(layout.keys(), pos))
        return layout

    @staticmethod
    def add_layout_to_vrnetz(
        nodes: pd.DataFrame, layout: dict, layout_name: str
    ) -> pd.DataFrame:
        """Adds the points of the generated layout to the underlying VRNetz

        Args:
            layout (dict): Dictionary containing node ids as keys and a 3-tuple of coordinates as values.
            layout_name (str): Name of the layout to be added to the VRNetz.

        Returns:
            pd.DataFrame: nodes data frame with added layout.
        """
        if NT.layouts in nodes:

            def extract_cy(x):
                if NT.layouts not in x:
                    return x
                layout = x[NT.layouts][0]
                x["cy_pos"] = layout["p"]
                x["cy_col"] = layout["c"]
                x["size"] = layout["s"]
                return x

            nodes = nodes.swifter.progress_bar(False).apply(extract_cy, axis=1)

        pos = np.array(list((layout.values())))
        _2d_layout = pos[:, :2]
        z_zero = np.zeros((len(layout), 1))
        _2d_layout = np.hstack((_2d_layout, z_zero))

        nodes[layout_name + "2d_pos"] = pd.Series(_2d_layout.tolist())
        nodes[layout_name + "_pos"] = pd.Series(pos.tolist())

        if "cy_pos" and "cy_col" in nodes:
            # Check if this works, as it now returns a np array
            coords = nodes["cy_pos"].to_dict()
            pos = np.array(list(Layouter.normalize_pos(coords, dim=2).values()))
            pos = np.hstack((pos, np.zeros((len(pos), 1))))
            nodes["cy_pos"] = pd.Series(pos.tolist())

            def extract_color(x):
                """Scale alpha channel (glowing effect) with node size (max size = 1"""
                col = x["cy_col"] + [int(255 * x["size"])]
                return col

            max_size = max(nodes["size"])
            nodes["size"] = (
                nodes["size"].swifter.progress_bar(False).apply(lambda x: x / max_size)
            )
            nodes["cy_col"] = (
                nodes[["cy_col", "size"]]
                .swifter.progress_bar(False)
                .apply(extract_color, axis=1)
            )

        return nodes

    @staticmethod
    def gen_evidence_layouts(
        links: pd.DataFrame,
        evidences: dict = None,
        stringify: bool = False,
    ) -> list[dict[str, object]]:
        """Set the link color for each STRING evidence type. Based on the score the link opacity is scaled.

        Args:
            network (dict): Network dictionary.
            evidences (dict[str, tuple[float, float, float, float]] or None, optional): Contains all possible evidence types and their corresponding color. Defaults to None.

        Returns:
            dict: Network dictionary with the link layout information.
        """
        # Set up the colors for each evidence type
        if evidences is None:
            evidences = Evidences.get_default_scheme()
        log.debug(f"Handling evidences...", flush=True)

        if ST.stringdb_score in links.columns:
            links = links.rename(columns={ST.stringdb_score: Evidences.any.value})

        elif Evidences.any.value not in links.columns:
            links[Evidences.any.value] = [1 for _ in range(len(links))]

        def extract_score(x):
            evidences = [
                ev for ev in Evidences.get_all_evidences_except_any() if ev in x.keys()
            ]
            if len(evidences) == 0:
                value = None
            else:
                value = max(x[evidences])
            x[Evidences.any.value] = value
            return x

        to_replace = links[Evidences.any.value].isnull()
        links[to_replace] = (
            links[to_replace].swifter.progress_bar(False).apply(extract_score, axis=1)
        )

        colors = [
            Layouter.handle_evidences(ev, color, links, stringify)
            for ev, color in evidences.items()
        ]
        for ev, data in zip(evidences.keys(), colors):
            if data is None:
                continue
            links[ev + "_col"] = data
        return links

    @staticmethod
    def handle_evidences(
        ev: str, color: list[int, int, int], links: pd.DataFrame, stringify: bool
    ):
        """Set the link color for each STRING evidence type. Based on the score the link opacity is scaled.

        Args:
            ev (str): Name of the evidence type.
            color (list[int, int, int]): color which belongs to the respective evidence type.
            links (pd.DataFrame): Data frame containing all the links.
            stringify (bool): Boolean which indicates whether the network is a STRING network or not, if not only the "any" evidence type is considered.
        """

        def gen_color(x, color):
            x = color[:3] + (int(x * 255),)
            return x

        if ev not in links.columns:
            if stringify:
                links[ev] = [int(0) for _ in range(len(links))]
            else:
                return
        with_score = links[links[ev] > 0.0][ev]
        this = with_score.swifter.progress_bar(False).apply(gen_color, args=(color,))
        return this


from . import layout_util


def sample_sphere(
    G: nx.Graph, layout: list[float, float, float], *args: tuple, **kwargs: dict
) -> dict[str, list[float, float, float]]:
    """Samples a sphere around the given layout for as many nodes as provided with the graph.

    Args:
        G (nx.Graph): Graph for which the points should be sampled.
        layout (list[float, float, float]): Layout containing the remaining points. Is used as the center of the sphere.

    Returns:
        dict[str, list[float, float, float]]: Dictionary containing the node names as keys and the sampled points as values.
    """
    n = len(G)
    pos = layout_util.sample_sphere_pcd(SAMPLE_POINTS=n, layout=layout, *args, **kwargs)
    layout = {}
    for i, node in enumerate(G.nodes()):
        layout[node] = pos[i]
    return layout


def visualize_layout(layout: list[float, float, float], *args, **kwargs):
    """Visualizes the given layout."""
    layout_util.visualize_layout(layout, *args, **kwargs)
