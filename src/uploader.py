import json
import os
import shutil
import sys

import pandas as pd
import swifter

import uploader as main_uploader

from .settings import _WORKING_DIR

sys.path.append(os.path.join(_WORKING_DIR, "..", ".."))

try:
    import GlobalData as GD
except ModuleNotFoundError:
    pass
from flask import jsonify
from PIL import Image

from .classes import AttrTags as AT
from .classes import Evidences as EV
from .classes import LayoutTags as LT
from .classes import LinkTags as LiT
from .classes import NodeTags as NT
from .classes import ProjectTag as PT
from .classes import StringTags as ST
from .classes import VRNetzElements as VRNE
from .settings import _MAPPING_ARBITARY_COLOR, _PROJECTS_PATH, log
from .util import clean_filename


def os_join(*args):
    return os.path.join(*args)


class Uploader:
    """Uploader class to upload VRNetz files.
    network (dict): network to be uploaded
    p_name (str): project name
    overwrite_project (bool, optional): Indicates whether to overwrite existing projects. Defaults to False.
    stringify (bool, optional): Is used to reflect STRING features, if the network is a string network. Defaults to True.
    p_path (str, optional): path to where the projects can be found. Defaults to None.
    """

    def __init__(
        self,
        network: dict,
        p_name: str,
        overwrite_project: bool = False,
        stringify: bool = True,
        p_path: str = None,
    ) -> None:
        if p_path is None:
            p_path = _PROJECTS_PATH

        self.network = network
        self.p_name = p_name  # Name of the project
        self.pf_path = p_path  # Path to the directory that contains all projects
        self.overwrite_project = overwrite_project  # boolean that indicates whether to skip existing project files or to update them
        self.stringify = (
            stringify  # boolean that indicates whether a network should be stringified
        )
        self.p_path = os_join(_PROJECTS_PATH, self.p_name)
        if self.overwrite_project:
            shutil.rmtree(self.p_path, ignore_errors=True)
        pfile = {"network": "NA"}
        pfile = {"network_type": "ppi"}
        if self.stringify:
            pfile["network"] = "string"

        self.names = {}
        pfile["name"] = self.p_name
        pfile["layouts"] = []
        pfile["layoutsRGB"] = []
        pfile["links"] = []
        pfile["linksRGB"] = []
        pfile["selections"] = []
        self.pfile = pfile
        self.nodes = {"nodes": []}
        self.links = {"links": []}
        self.p_path = os_join(_PROJECTS_PATH, self.p_name)  # Path to project dir
        self.layout_dir = os_join(self.p_path, "layouts")  # Path to layouts dir
        self.layoutsl_dir = os_join(
            self.p_path, "layoutsl"
        )  # Path to layouts lower dir
        self.layouts_rgb_dir = os_join(
            self.p_path, "layoutsRGB"
        )  # Path to layouts RGB dir
        self.links_dir = os_join(self.p_path, "links")  # Path to links dir
        self.links_rgb_dir = os_join(self.p_path, "linksRGB")  # Path to links RGB dir
        self.pfile_file = os_join(self.p_path, "pfile.json")  # Path to pfile
        self.names_file = os_join(self.p_path, "names.json")  # Path to names file
        self.nodes_file = os_join(self.p_path, "nodes.json")  # Path to nodes files
        self.links_file = os_join(self.p_path, "links.json")  # Path to links file
        self.MAX_NUM_LINKS = 262144

    def makeProjectFolders(self) -> None:
        """Creates the project folders and writes empty pfile and names file."""

        path = self.p_path

        os.makedirs(path, exist_ok=os.X_OK)
        os.makedirs(os_join(path, "layouts"), exist_ok=os.X_OK)
        os.makedirs(os_join(path, "layoutsl"), exist_ok=os.X_OK)
        os.makedirs(os_join(path, "layoutsRGB"), exist_ok=os.X_OK)
        os.makedirs(os_join(path, "links"), exist_ok=os.X_OK)
        os.makedirs(os_join(path, "linksRGB"), exist_ok=os.X_OK)

        with open(self.pfile_file, "w") as outfile:
            json.dump(self.pfile, outfile)

        with open(self.names_file, "w") as outfile:
            json.dump(self.names, outfile)

        rel_path = path.find("static")
        rel_path = path[rel_path:]
        log.debug(f"Successfully created directories in {rel_path}")
        log.debug(f"Full Path {path}")

    def write_json_files(self) -> None:
        """Will update the project files: pfile, names, nodes, links"""
        files = [
            self.pfile_file,
            self.names_file,
            self.nodes_file,
            self.links_file,
        ]

        contents = [
            self.pfile,
            self.names,
            self.nodes,
            self.links,
        ]

        for file, content in zip(
            files,
            contents,
        ):
            with open(file, "w") as json_file:
                json.dump(content, json_file)

    def read_json_files(self) -> None:
        """Will readout all json files in the project folder."""
        files = [self.pfile_file, self.names_file, self.nodes_file, self.links_file]

        contents = ["pfile", "names", "nodes", "links"]
        for file, content in zip(
            files,
            contents,
        ):
            with open(file, "r") as json_file:
                self.__dict__[content] = json.load(json_file)

    def make_link_tex(self, links: dict, layouts: list) -> str:
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

        height = 512
        path = self.p_path

        def get_pixel(elem):
            if pd.isnull(elem):
                return (0, 0, 0)
            sx = elem % 128
            syl = elem // 128 % 128
            syh = elem // 16384
            elem = (int(sx), int(syl), int(syh))
            return elem

        tmp = links.copy()
        tmp["start_pix"] = links[LiT.start].swifter.apply(get_pixel)
        tmp["end_pix"] = links[LiT.end].swifter.apply(get_pixel)
        # links = links.drop(columns=[LiT.layouts])
        # print(nodes.iloc[0]["cy_color"])
        # exit()
        tmp = tmp.fillna(0)
        path = self.p_path
        output = ""
        for layout in [c for c in links.columns if c in EV.get_all_evidences()]:

            colors = tmp[layout + "_col"][: self.MAX_NUM_LINKS]
            colors = colors.astype("object")
            image = Image.new("RGBA", (512, height))
            rgb = f"{layout}RGB"
            image.putdata(colors.to_numpy())
            image.save(os_join(path, "linksRGB", f"{rgb}.png"))

            if rgb not in self.pfile["linksRGB"]:
                self.pfile["linksRGB"].append(rgb)

            if tmp["start_pix"].any() or tmp["end_pix"].any():
                starts = tmp["start_pix"].fillna(0)
                ends = tmp["end_pix"].fillna(0)

                # Cut data frame to max number of links

                texture = pd.concat([starts, ends]).sort_index(kind="stable")[
                    : self.MAX_NUM_LINKS
                ]  # sort the entries in an alternating fashion
                texture = texture.to_numpy()
                xyz = f"{layout}XYZ"
                image = Image.new("RGB", (1024, height))
                image.putdata(texture)
                image.save(os_join(path, "links", f"{xyz}.bmp"))

                if xyz not in self.pfile["links"]:
                    self.pfile["links"].append(xyz)

            output += (
                '<br><a style="color:green;">SUCCESS </a>'
                + layout
                + " Link Textures Created"
            )
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
            self.pfile[PT.links] = ev_xyz  # [ev_xyz[0], ev_xyz[0]] + ev_xyz
            self.pfile[PT.links_rgb] = ev_rgb  # [ev_rgb[0], ev_rgb[0]] + ev_rgb
        if nodes:
            if f"{LT.cy_layout}XYZ" in self.pfile[PT.layouts]:
                self.pfile[PT.layouts].remove(f"{LT.cy_layout}XYZ")
                tmp = self.pfile[PT.layouts]
                self.pfile[PT.layouts] = [f"{LT.cy_layout}XYZ"] + tmp

        with open(self.pfile_file, "w") as json_file:
            json.dump(self.pfile, json_file)

    def make_node_tex(
        self,
        nodes: list[dict],
        layouts: list[str],
        skip_attr: list[str] = ["layouts"],
    ):
        """Extract all Node data from the network.

        Args:
            nodes (list[dict]): Contains all nodes of the network as key, value pairs.
            skip_attr (list[str]): Contains all attributes that should be skipped.
            layouts (list[str]): Contains all layouts for which positions should be extracted.
        """
        if not isinstance(nodes, pd.DataFrame):
            nodes = pd.DataFrame(nodes)
        nodes = self.change_to_universal_attr(nodes)
        # filtered = nodes.drop(columns=skip_attr)
        # self.nodes[VRNE.nodes] += filtered.to_dict(orient="records")
        n = len(nodes)
        nodes: pd.DataFrame
        if "names" not in self.names:
            self.names["names"] = []
        self.names["names"] = [[n] for n in nodes[NT.name].tolist()]
        if NT.display_name in self.names:
            self.names[NT.display_name] = [[n] for n in nodes[NT.display_name].tolist()]

        hight = 128 * (int(n / 16384) + 1)

        size = 128 * hight
        path = self.p_path
        output = ""

        for layout in [c for c in nodes.columns if c.endswith("_pos")]:
            layout_name = layout.replace("_pos", "")
            if not nodes[layout].any():
                continue
            pos = nodes[layout].swifter.apply(
                lambda x: [int(float(value) * 65280) for value in x]
            )

            t_high = pos.swifter.apply(
                lambda x: tuple(value // 255 for value in x)
            ).fillna(0)
            t_low = pos.swifter.apply(
                lambda x: tuple(value % 255 for value in x)
            ).fillna(0)

            images = {k: Image.new("RGB", (128, hight)) for k in ["high", "low"]}
            images["layoutsRGB"] = Image.new("RGBA", (128, hight))

            for key, data in zip(["high", "low"], [t_high, t_low]):
                images[key].putdata(data)
            images["high"]

            xyz = f"{layout_name}XYZ"
            images["high"].save(os_join(path, "layouts", f"{xyz}.bmp"))
            images["low"].save(os_join(path, "layoutsl", f"{xyz}l.bmp"))
            if xyz not in self.pfile["layouts"]:
                self.pfile["layouts"].append(xyz)

            color = layout.replace("_pos", "_col")
            if color in nodes.columns:
                if not nodes[color].any():
                    continue
                color = nodes[color]
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

                color = color.swifter.apply(set_color)
                images["layoutsRGB"].putdata(color)

                rgb = f"{layout_name}RGB"
                images["layoutsRGB"].save(os_join(path, "layoutsRGB", f"{rgb}.png"))

                if rgb not in self.pfile["layoutsRGB"]:
                    self.pfile["layoutsRGB"].append(rgb)

            output += (
                '<br><a style="color:green;">SUCCESS </a>'
                + layout_name
                + " Node Textures Created"
            )
        return output

    def upload_files(
        self,
        network: dict,
    ) -> str:
        """Generates textures and upload the needed network files. If created_2d_layout is True, it will create 2d layouts of the network one based on the cytoscape coordinates and one based on the new coordinated that come from the 3D layout without the z-coordinate.
        Furthermore, for each STRING evidence a edge texture with the respective color will be generated. If it is not a STRING network, only a single edge layout called "any" is created.

        Args:
            network (dict): Has to have the following keys: nodes, links, node_layouts, link_layouts

        Returns:
            str: status message of the upload
        """
        project = clean_filename(self.p_name)

        # Set up project directories
        prolist = main_uploader.listProjects()

        if self.overwrite_project:
            self.makeProjectFolders()
        else:
            if project in prolist:
                log.debug(f"Project: {project} already exists.")
            else:
                # Make Folders
                self.makeProjectFolders()

        state = ""

        nodes = network.get(VRNE.nodes)
        links = network.get(VRNE.links)
        n_lay = network.get(VRNE.node_layouts, [])  # Node layouts
        l_lay = network.get(VRNE.link_layouts, [])  # Link layouts

        with open(self.names_file, "r") as json_file:
            self.names = json.load(json_file)

        with open(self.pfile_file, "r") as json_file:
            self.pfile = json.load(json_file)

        state += self.make_node_tex(nodes, layouts=n_lay)

        state += self.make_link_tex(links, l_lay)

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
        layouts = [c for c in self.pfile["layouts"]]
        cy = [c for c in layouts if "cy" in c]
        two = [c for c in layouts if "2d" in c]
        rest = [c for c in layouts if c not in cy and c not in two]
        layouts = cy + two + rest
        self.pfile["layouts"] = [f"{c}" for c in layouts]

        layouts_rgb = [c for c in self.pfile["layoutsRGB"]]
        cy = [c for c in layouts_rgb if "cy" in c]
        two = [c for c in layouts_rgb if "2d" in c]
        rest = [c for c in layouts_rgb if c not in cy and c not in two]
        layouts_rgb = cy + two + rest
        self.pfile["layoutsRGB"] = [f"{c}" for c in layouts_rgb]

        self.nodes = {"nodes": [v.dropna().to_dict() for k, v in nodes.iterrows()]}
        self.links = {"links": [v.dropna().to_dict() for k, v in links.iterrows()]}
        self.write_json_files()

        if self.stringify:
            self.stringify_project()

        try:
            GD.sessionData["proj"] = main_uploader.listProjects()
        except NameError:
            pass

        return state

    def color_nodes(
        self,
        target_project: str,
        mapping_color: list[int, int, int] = _MAPPING_ARBITARY_COLOR,
        update_link_textures: bool = True,
        skip_attr=["layouts"],
    ):
        """Will color all node in the target project to the color of the corresponding node in the source project to reflect the mapped nodes.
        Node which are not mapped will be colored in the mapping color and will glow less.

        Args:
            target_project (str): name of the target project
            mapping_color (list[int], optional): color (RGB) of not mapped nodes. Defaults to [255, 255, 255].
        """
        self.read_json_files()
        target_links = self.pfile[PT.links]
        target_links_rgb = self.pfile[PT.links_rgb]

        layouts = self.pfile["layoutsRGB"]
        l_lay = [ev.value for ev in EV]

        self.links = {"links": []}
        links = self.network.get(VRNE.links)

        if update_link_textures:
            self.make_link_tex(links, l_lay)
            self.stringify_project(nodes=False)

            self.pfile[PT.links] += [
                link for link in target_links if "stringdb" not in link
            ]
            self.pfile[PT.links_rgb] += [
                link for link in target_links_rgb if "stringdb" not in link
            ]

        self.nodes = {"nodes": []}  # Reset nodes
        nodes = pd.DataFrame(self.network.get(VRNE.nodes))
        nodes = self.change_to_universal_attr(nodes)
        filtered = nodes.copy()
        for key in skip_attr:
            if key in nodes.columns:
                filtered = filtered.drop(columns=[key])

        self.nodes = {"nodes": [v.dropna().to_dict() for k, v in filtered.iterrows()]}

        self.links = {"links": [v.dropna().to_dict() for k, v in links.iterrows()]}

        # with open(self.links_file, "r") as json_file:
        #     self.links = json.load(json_file)

        self.write_json_files()
        for l, layout in enumerate(layouts):
            pathRGB = os_join(target_project, "layoutsRGB", f"{layout}.png")
            img = Image.open(pathRGB)

            def get_color(elem):
                if elem[NT.node_color] == mapping_color:
                    return tuple(elem[NT.node_color] + [50])
                else:
                    return tuple(elem[NT.node_color] + [255 // 2])

            data = nodes.swifter.apply(get_color, axis=1)
            img.putdata(data)

            img.save(os_join(self.p_path, "layoutsRGB", f"{layout}.png"))

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
