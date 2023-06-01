import os
import sys
import warnings
from multiprocessing import Manager, Pool, Process

import numpy as np
import pandas as pd
import swifter

import uploader as main_uploader

from .settings import _WORKING_DIR

sys.path.append(os.path.join(_WORKING_DIR, "..", ".."))

import GlobalData as GD
from PIL import Image
from project import COLOR, DEFAULT_PFILE, NODE, Project

from .classes import Evidences as EV
from .classes import LayoutTags as LT
from .classes import LinkTags as LiT
from .classes import NodeTags as NT
from .classes import ProjectTag as PT
from .classes import StringTags as ST
from .classes import VRNetzElements as VRNE
from .settings import log
from .util import clean_filename

warnings.filterwarnings("ignore")


def os_join(*args):
    return os.path.join(*args)


class Uploader:
    """Uploader class to upload VRNetz files.
    network (dict): network to be uploaded
    p_name (str): project name
    overwrite_project (bool, optional): Indicates whether to overwrite existing projects. Defaults to False.
    stringify (bool, optional): Is used to reflect STRING features, if the network is a string network. Defaults to True.
    """

    def __init__(
        self,
        network: dict,
        p_name: str,
        overwrite_project: bool = False,
        stringify: bool = True,
    ) -> None:
        self.network = network
        self.project = Project(p_name)
        self.overwrite_project = overwrite_project  # boolean that indicates whether to skip existing project files or to update them
        self.stringify = (
            stringify  # boolean that indicates whether a network should be stringified
        )
        if self.overwrite_project:
            self.project.remove()
            self.project = Project(p_name)
        if self.project.pfile is None:
            self.project.pfile = DEFAULT_PFILE
        self.project.pfile["name"] = p_name
        if self.stringify:
            self.project.pfile["network"] = "string"
        self.project.pfile["network_type"] = "ppi"
        self.project.pfile["nodecount"] = 0
        self.project.pfile["linkcount"] = 0
        self.project.pfile["labelcount"] = 0
        self.MAX_NUM_LINKS = 262144
        # TODO: PFILE IS WRONGLY WRITTEN LINKS AND LINKSRGB IS SWITCHED

    def makeProjectFolders(self) -> None:
        """Creates the project folders and writes empty pfile and names file."""

        self.project.create_all_directories()
        rel_path = self.project.location.find("static")
        rel_path = self.project.location[rel_path:]
        log.debug(f"Successfully created directories in {rel_path}.", flush=True)
        log.debug(f"Full Path {self.project.location}.", flush=True)

    def handle_link_layout(
        self,
        layout: str,
        all_colors: pd.DataFrame,
        start: pd.Series,
        end: pd.Series,
        path: str,
        height: int,
    ) -> dict:
        """
        Handle a respective link layout and generate the respective bitmaps.

        Args:
            layout (str): layout name.
            all_colors (pd.DataFrame): contains all colors for the links.
            start (pd.Series): contains all start positions for the links.
            end (pd.Series): contains all end positions for the links.
            path (str): path to the project folder.
            height (int): height of the image.

        Returns:
            dict: contains the status message and the names of the generated files.

        """
        colors = all_colors[: self.MAX_NUM_LINKS].copy()
        layout_name = layout.replace("_col", "")
        colors = colors.swifter.progress_bar(False).apply(
            lambda x: x
            if x != (0, 0, 0, 0)
            and x != "<NA>"
            and x != np.nan
            and not isinstance(x, float)
            else pd.NA
        )
        colors = colors.fillna(0)
        image = Image.new("RGBA", (512, height))
        rgb = f"{layout_name}RGB"
        xyz = None
        image.putdata(colors)
        image.save(os_join(path, "linksRGB", f"{rgb}.png"))

        if start.any() or end.any():
            start = start.fillna(0)
            end = end.fillna(0)

            # Cut data frame to max number of links

            texture = pd.concat([start, end]).sort_index(kind="stable")[
                : self.MAX_NUM_LINKS
            ]  # sort the entries in an alternating fashion
            texture = texture.to_numpy()
            xyz = f"{layout_name}XYZ"
            image = Image.new("RGB", (1024, height))
            image.putdata(texture)
            image.save(os_join(path, "links", f"{xyz}.bmp"))

        res = {
            "out": (
                '<br><a style="color:green;">SUCCESS </a>'
                + layout_name
                + " Link Textures Created"
            ),
            "rgb": rgb,
            "xyz": xyz,
        }
        return res

    def make_link_tex(
        self,
        links: dict,
        layouts: list,
        return_dict: dict = None,
        parallel: bool = False,
    ) -> None or list[dict]:
        """Generate a Link texture from a dictionary of edges.

        Args:
            links (dict): contains all links of the network.
            layouts (list): contains all layouts for which the output should be generated.

        Returns:
            str: status message to report the status of the execution.
        """
        if not isinstance(links, pd.DataFrame):
            links = pd.DataFrame(links)
        # for layout in layouts:
        #     links[layout] = [None for _ in range(len(links))]
        # links["start_tex"] = [None for _ in range(len(links))]
        # links["end_tex"] = [None for _ in range(len(links))]

        # filtered = links[[LiT.id, LiT.start, LiT.end]]
        # self.links[VRNE.links] += filtered.to_dict(orient="records")
        log.debug("Handling Links..")
        height = 512
        path = self.project.location

        tmp = links.copy()
        tmp["start_pix"] = links[LiT.start].apply(
            lambda x: (x % 128, x // 128 % 128, x // 16384)
            if not pd.isnull(x)
            else (0, 0, 0)
        )
        tmp["end_pix"] = links[LiT.end].apply(
            lambda x: (x % 128, x // 128 % 128, x // 16384)
            if not pd.isnull(x)
            else (0, 0, 0)
        )
        path = self.project.location
        layouts = [c for c in links.columns if c.endswith("col")]
        args = []
        for lay in layouts:
            layout = tmp[lay].copy()
            args.append(
                (
                    lay,
                    layout,
                    tmp["start_pix"],
                    tmp["end_pix"],
                    path,
                    height,
                )
            )
        if parallel:
            pool = Pool()
            output = pool.starmap(self.handle_link_layout, args)
            pool.close()
            return_dict["links"] = output
        else:
            output = []
            for arg in args:
                output.append(self.handle_link_layout(*arg))
            return output

    def stringify_project(self, links: bool = True, nodes: bool = True):
        """Only adds the evidences to pfile layouts.

        Args:
            links (bool, optional): Wether to add string specific node layouts. Defaults to True.
            nodes (bool, optional): Whether to add string specific edge layouts. Defaults to True.
        """
        ev = EV.get_default_scheme().keys()
        ev_xyz = [f"{ev}XYZ" for ev in ev]
        ev_rgb = [f"{ev}RGB" for ev in ev]
        if links:
            self.project.pfile[PT.links] = ev_xyz  # [ev_xyz[0], ev_xyz[0]] + ev_xyz
            self.project.pfile[PT.links_rgb] = ev_rgb  # [ev_rgb[0], ev_rgb[0]] + ev_rgb
        if nodes:
            if f"{LT.cy_layout}XYZ" in self.project.pfile[PT.layouts]:
                self.project.pfile[PT.layouts].remove(f"{LT.cy_layout}XYZ")
                tmp = self.project.pfile[PT.layouts]
                self.project.pfile[PT.layouts] = [f"{LT.cy_layout}XYZ"] + tmp

        self.project.write_pfile()

    def handle_node_layout(
        self, layout: str, pos: pd.Series, color: pd.Series, path: str, hight: int
    ) -> dict:
        """Handles the creation of a node layout.

        Args:
            layout (str): layout name.
            pos (pd.Series): coordinates of the nodes.
            color (pd.Series): color of the nodes.
            path (str): path to the project folder.
            hight (int): hight of the image.

        Returns:
            dict: status message to report the status of the execution.
        """
        layout_name = layout.replace("_pos", "")
        xyz = None
        rgb = None
        if pos is not None and pos.any():
            pos = pos.swifter.progress_bar(False).apply(
                lambda x: [int(float(value) * 65280) for value in x]
            )

            t_high = (
                pos.swifter.progress_bar(False)
                .apply(lambda x: tuple(value // 255 for value in x))
                .fillna(0)
            )
            t_low = (
                pos.swifter.progress_bar(False)
                .apply(lambda x: tuple(value % 255 for value in x))
                .fillna(0)
            )

            images = {k: Image.new("RGB", (128, hight)) for k in ["high", "low"]}
            images["layoutsRGB"] = Image.new("RGBA", (128, hight))

            for key, data in zip(["high", "low"], [t_high, t_low]):
                images[key].putdata(data)
            images["high"]

            xyz = f"{layout_name}XYZ"
            images["high"].save(os_join(path, "layouts", f"{xyz}.bmp"))
            images["low"].save(os_join(path, "layoutsl", f"{xyz}l.bmp"))

        if color is not None and color.any():
            color = color.fillna(0)

            def set_color(x):
                if len(x) == 4:
                    return tuple(
                        x,
                    )
                elif x == 0:
                    return x
                return tuple(
                    x
                    + [
                        255 // 2,
                    ],
                )

            color = color.swifter.progress_bar(False).apply(set_color)
            images["layoutsRGB"].putdata(color)

            rgb = f"{layout_name}RGB"
            images["layoutsRGB"].save(os_join(path, "layoutsRGB", f"{rgb}.png"))

        res = {
            "out": '<br><a style="color:green;">SUCCESS </a>'
            + layout_name
            + " Node Textures Created",
            "rgb": rgb,
            "xyz": xyz,
        }
        return res

    def make_node_tex(
        self,
        nodes: list[dict],
        layouts: list[str],
        skip_attr: list[str] = ["layouts"],
        return_dict: dict = None,
        parallel: bool = False,
    ) -> None or list[dict]:
        """Extract all Node data from the network.

        Args:
            nodes (list[dict]): Contains all nodes of the network as key, value pairs.
            skip_attr (list[str]): Contains all attributes that should be skipped.
            layouts (list[str]): Contains all layouts for which positions should be extracted.
        """
        if not isinstance(nodes, pd.DataFrame):
            nodes = pd.DataFrame(nodes)
        # nodes = self.change_to_universal_attr(nodes)
        # filtered = nodes.drop(columns=skip_attr)
        # self.nodes[VRNE.nodes] += filtered.to_dict(orient="records")
        n = len(nodes)
        hight = 128 * (int(n / 16384) + 1)

        path = self.project.location
        layouts = [c for c in nodes.columns if c.endswith("_pos")]
        colors = [c for c in nodes.columns if c.endswith("_col")]
        n = len(layouts)
        if len(colors) > n:
            n = len(colors)
        args = []

        for idx in range(n):
            if idx < len(layouts):
                lay = layouts[idx]
                layout = nodes[lay].copy()
            else:
                layout = None
                lay = None
            if idx < len(colors):
                color = colors[idx]
                color = nodes[color].copy()
            else:
                color = None
            args.append(
                (
                    lay,
                    layout,
                    color,
                    path,
                    hight,
                )
            )
        if parallel:
            n = len(layouts)
            pool = Pool(n)
            output = pool.starmap(
                self.handle_node_layout,
                args,
            )
            pool.close()
            return_dict["nodes"] = output
        else:
            output = []
            for arg in args:
                output.append(self.handle_node_layout(*arg))
            return output

    def upload_files(
        self,
        network: dict,
        parallel: bool = True,
    ) -> str:
        """Generates textures and upload the needed network files. If created_2d_layout is True, it will create 2d layouts of the network one based on the cytoscape coordinates and one based on the new coordinated that come from the 3D layout without the z-coordinate.
        Furthermore, for each STRING evidence a edge texture with the respective color will be generated. If it is not a STRING network, only a single edge layout called "any" is created.

        Args:
            network (dict): Has to have the following keys: nodes, links, node_layouts, link_layouts

        Returns:
            str: status message of the upload
        """
        log.debug("Handling Nodes...")
        project = clean_filename(self.project.name)

        # Set up project directories
        prolist = GD.listProjects()

        if self.overwrite_project:
            self.makeProjectFolders()
        else:
            if project in prolist:
                log.warning(f"Project: {project} already exists.")
            else:
                # Make Folders
                self.makeProjectFolders()

        nodes = network.get(VRNE.nodes)
        links = network.get(VRNE.links)
        n_lay = network.get(VRNE.node_layouts, [])  # Node layouts
        l_lay = network.get(VRNE.link_layouts, [])  # Link layouts
        if self.project.names is None:
            self.project.names = {}

        if "names" not in self.project.names:
            self.project.names["names"] = []
        self.project.names["names"] = [[n] for n in nodes[NT.name].tolist()]
        if NT.display_name in self.project.names:
            self.project.names[NT.display_name] = [
                [n] for n in nodes[NT.display_name].tolist()
            ]
        if parallel:
            node_tex_res, link_tex_res = self.parallel_process(
                nodes, links, n_lay, l_lay
            )
        else:
            node_tex_res = self.make_node_tex(nodes, n_lay)
            link_tex_res = self.make_link_tex(links, l_lay)
        state = ""
        for res in node_tex_res:
            state += res["out"]
            if res["xyz"] and res["xyz"] not in self.project.pfile["layouts"]:
                self.project.pfile["layouts"].append(res["xyz"])
            if res["rgb"] and res["rgb"] not in self.project.pfile["layoutsRGB"]:
                self.project.pfile["layoutsRGB"].append(res["rgb"])

        for res in link_tex_res:
            state += res["out"]
            if res["xyz"] and res["xyz"] not in self.project.pfile["links"]:
                self.project.pfile["links"].append(res["xyz"])
            if res["rgb"] and res["rgb"] not in self.project.pfile["linksRGB"]:
                self.project.pfile["linksRGB"].append(res["rgb"])
        nodes = self.network.get(VRNE.nodes, [])

        if isinstance(nodes, pd.DataFrame):
            drops = (
                [c for c in nodes.columns if c.endswith("_pos")]
                + [c for c in nodes.columns if c.endswith("_col")]
                + ["size"]
            )
            for c in drops:
                if c in nodes.columns:
                    nodes = nodes.drop(columns=[c])
        links = self.network.get(VRNE.links, [])

        if isinstance(links, pd.DataFrame):
            drops = [c for c in links.columns if c.endswith("_col")] + ["size"]
            for c in drops:
                if c in links.columns:
                    links = links.drop(columns=[c])
        # Sort layouts so that Cytoscape is first followed by 2d and then the rest
        layouts = [c for c in self.project.pfile["layouts"]]
        cy = [c for c in layouts if "cy" in c]
        two = [c for c in layouts if "2d" in c]
        rest = [c for c in layouts if c not in cy and c not in two]
        layouts = cy + two + rest
        self.project.pfile["layouts"] = [f"{c}" for c in layouts]

        layouts_rgb = [c for c in self.project.pfile["layoutsRGB"]]
        cy = [c for c in layouts_rgb if "cy" in c]
        two = [c for c in layouts_rgb if "2d" in c]
        rest = [c for c in layouts_rgb if c not in cy and c not in two]
        layouts_rgb = cy + two + rest
        self.project.pfile["layoutsRGB"] = [f"{c}" for c in layouts_rgb]

        nodes = nodes[[c for c in nodes.columns if not c.endswith(("_pos", "_col"))]]
        links = links[[c for c in links.columns if not c.endswith(("_col",))]]
        self.project.nodes = {
            "nodes": [v.dropna().to_dict() for k, v in nodes.iterrows()]
        }
        self.project.links = {
            "links": [v.dropna().to_dict() for k, v in links.iterrows()]
        }
        self.project.pfile["nodecount"] = len(nodes)
        self.project.pfile["linkcount"] = len(links)
        self.project.write_all_jsons()
        if self.stringify:
            self.stringify_project()
        try:
            GD.loadGD()
        except Exception as e:
            log.error(e)
            pass

        return state

    def color_nodes(
        self,
        target_project: str,
        update_link_textures: bool = True,
        skip_attr=["layouts"],
    ):
        """Will color all node in the target project to the color of the corresponding node in the source project to reflect the mapped nodes.
        Node which are not mapped will be colored in the mapping color and will glow less.

        Args:
            target_project (str): name of the target project
            mapping_color (list[int], optional): color (RGB) of not mapped nodes. Defaults to [255, 255, 255].
        """
        self.project.read_all_jsons()
        target_links = self.project.get_pfile_value(PT.links)
        target_links_rgb = self.project.get_pfile_value(PT.links_rgb)

        layouts = self.project.get_pfile_value(PT.layouts_rgb)
        l_lay = [ev.value for ev in EV]

        # if update_link_textures:
        #     p = Process(
        #         target=self.update_link_textures,
        #         args=(
        #             links,
        #             l_lay,
        #             target_links,
        #             target_links_rgb,
        #         ),
        #     )
        #     p.start()

        self.project.nodes = {"nodes": []}  # Reset nodes
        nodes = pd.DataFrame(self.network.get(VRNE.nodes))
        nodes = self.change_to_universal_attr(nodes)

        filtered = nodes.copy()
        for key in skip_attr:
            if key in nodes.columns:
                filtered = filtered.drop(columns=[key])

        nodes["From Cytoscape"] = None
        mapped_nodes = nodes[~nodes[NT.size].isna()].copy()
        not_mappend = nodes[nodes[NT.size].isna()].copy()
        mapped_nodes["From Cytoscape"] = [True] * len(mapped_nodes)
        not_mappend["From Cytoscape"] = [False] * len(not_mappend)

        nodes.update(mapped_nodes)
        nodes.update(not_mappend)

        self.project.nodes = {
            "nodes": [
                {
                    k: v
                    for k, v in m.items()
                    if pd.api.types.is_list_like(v) or pd.notnull(v)
                }
                for m in nodes.to_dict(orient="rows")
            ]
        }

        self.project.links = {"links": []}
        links = self.network.get(VRNE.links)

        self.project.links = {
            "links": [
                {
                    k: v
                    for k, v in m.items()
                    if pd.api.types.is_list_like(v) or pd.notnull(v)
                }
                for m in links.to_dict(orient="rows")
            ]
        }

        nodes = nodes.drop(
            columns=[c for c in nodes.columns if c not in [NT.node_color, NT.size]]
        )

        def mask_nodes(project: Project, nodes: pd.DataFrame, selected_nodes: list):
            # MASK WHICH HIGHLIGHTS NODES THAT ARE SELECTED
            NODE_BITMAP_SIZE = 128
            nodes = pd.DataFrame(project.get_nodes()["nodes"])
            mask = np.zeros((NODE_BITMAP_SIZE, NODE_BITMAP_SIZE, 4))
            nodes = nodes[nodes["id"].isin(selected_nodes)].copy()
            x, y = nodes["id"] // NODE_BITMAP_SIZE, nodes["id"] % NODE_BITMAP_SIZE
            x, y = x.astype(int), y.astype(int)
            mask[x, y, :] = 1
            return mask

        mask = mask_nodes(self.project, nodes, mapped_nodes.index)
        for lay in layouts:
            layout_bmp = self.project.load_bitmap(lay, NODE, COLOR, True)
            selected = np.zeros_like(layout_bmp)
            selected[layout_bmp > 0] = mask[layout_bmp > 0]
            # Multiply the two images element-wise
            if len(np.unique(layout_bmp)) >= 1:
                # If not all colors are the same, use the color of the selected nodes.
                result = layout_bmp * selected
            else:
                # Else mask selected nodes red.
                result[:, :, :3] = [255, 0, 0]

            non_zero = np.nonzero(selected)
            NOT_SELECTED = (
                255,
                255,
                255,
                10,
            )
            max_row = np.max(non_zero[0])
            non_zero = np.nonzero(selected[max_row])
            max_col = np.max(non_zero[0])
            not_selected = ~selected
            not_selected[:max_row, :, :] = NOT_SELECTED
            not_selected[max_row, :max_col, :] = NOT_SELECTED
            not_selected[max_row, max_col:, :] = NOT_SELECTED
            not_selected[max_row + 1 :, :, :] = NOT_SELECTED

            result = result + not_selected
            bmp = Image.fromarray(np.uint8(result))
            self.project.write_bitmap(bmp, lay, NODE, COLOR)

        # color layout which just highlights the mapped nodes
        mapped_nodes[NT.node_color] = mapped_nodes.swifter.progress_bar(False).apply(
            lambda x: tuple(x[NT.node_color] + [int(255 * x[NT.size])]), axis=1
        )

        not_mappend[NT.node_color] = (
            not_mappend[NT.node_color]
            .swifter.progress_bar(False)
            .apply(lambda x: tuple(x + [50]))
        )
        nodes = pd.concat([mapped_nodes, not_mappend])
        nodes = nodes.sort_index()
        layout_bmp = Image.new("RGBA", (128, 128))
        layout_bmp.putdata(nodes[NT.node_color])
        self.project.write_bitmap(layout_bmp, "Mapped", NODE, COLOR)
        self.project.add_node_color("Mapped")

        self.project.write_all_jsons()

    def update_link_textures(self, links, l_lay, target_links, target_links_rgb):
        self.make_link_tex(links, l_lay)
        self.stringify_project(nodes=False)
        self.project.pfile[PT.links] += [
            link for link in target_links if "stringdb" not in link
        ]
        self.project.pfile[PT.links] += [
            link for link in target_links_rgb if "stringdb" not in link
        ]

    def change_to_universal_attr(self, nodes: pd.DataFrame) -> dict:
        """Rename STRING DB attributes to vrnetzer universal attributes so they will be displayed at the correct place on the node panel

        Args:
            node (pd.DataFrame): Nodes to change.

        Returns:
            dict: Nodes with changed attribute keys.
        """
        universal_attributes = [NT.description, NT.sequence, NT.species]
        string_attributes = [
            ST.stringdb_description,
            ST.stringdb_sequence,
            ST.stringdb_species,
        ]
        for u_att, s_attr in zip(universal_attributes, string_attributes):
            if s_attr in nodes.columns:
                nodes.rename(columns={s_attr: u_att}, inplace=True)
        return nodes

    def parallel_process(self, nodes, links, n_lay, l_lay):
        manager = Manager()
        return_dict = manager.dict()
        processes = []
        if len(n_lay) > os.cpu_count():
            log.debug("Parallel node layout creation", flush=True)
            np = Process(
                target=self.make_node_tex,
                args=(
                    nodes,
                    n_lay,
                ),
                kwargs={"return_dict": return_dict, "parallel": True},
            )
            processes.append(np)
        else:
            return_dict["nodes"] = self.make_node_tex(nodes, n_lay)
        if len(l_lay) > os.cpu_count():
            log.debug("Parallel link layout Creation", flush=True)
            lp = Process(
                target=self.make_link_tex,
                args=(
                    links,
                    l_lay,
                ),
                kwargs={"return_dict": return_dict, "parallel": True},
            )
            processes.append(lp)
        else:
            return_dict["links"] = self.make_link_tex(links, l_lay)

        for p in processes:
            p.start()

        for p in processes:
            p.join()

        node_tex_res = return_dict["nodes"]
        link_tex_res = return_dict["links"]
        return node_tex_res, link_tex_res
