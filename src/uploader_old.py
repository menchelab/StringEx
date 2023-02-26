import json
import os
import shutil
import sys

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
        self.p_path = os_join(_PROJECTS_PATH, self.p_name)
        self.pfile_file = os_join(self.p_path, "pfile.json")
        self.names_file = os_join(self.p_path, "names.json")
        self.nodes_file = os_join(self.p_path, "nodes.json")
        self.links_file = os_join(self.p_path, "links.json")

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

    def loadProjectInfo(self) -> dict or str:
        """List the project information.

        Returns:
            dict or str: Contains the project information or a string if the project does not exist.
        """
        self.folder = os_join(self.p_path)
        self.layoutfolder = os_join(self.folder, "layouts")
        self.layoutRGBfolder = os_join(self.folder, "layoutsRGB")
        self.linksRGBfolder = os_join(self.folder, "linksRGB")
        self.linkfolder = os_join(self.folder, "links")

        if os.path.exists(self.folder):

            layouts = [name for name in os.listdir(self.layoutfolder)]
            layoutsRGB = [name for name in os.listdir(self.layoutRGBfolder)]
            links = [name for name in os.listdir(self.linkfolder)]
            linksRGB = [name for name in os.listdir(self.linksRGBfolder)]

            return jsonify(
                layouts=layouts, layoutsRGB=layoutsRGB, links=links, linksRGB=linksRGB
            )
        else:
            return "no such project"

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

    @staticmethod
    def loadAnnotations(projects_path: str = _PROJECTS_PATH) -> dict:
        """Return all annotations corresponding to a project name.

        Args:
            p_path (str): path to where the projects can be found.

        Returns:
            dict: annotations contained in the names.json file of the project.
        """
        namefile = os_join(projects_path, "names.json")
        f = open(namefile)
        data = json.load(f)
        return data

    @staticmethod
    def listProjects(projects_path: str = _PROJECTS_PATH) -> list:
        """Returns a list of all projects.

        Args:
            projects_path (str, optional): Path to where projects can be found. Defaults to _PROJECTS_PATH.

        Returns:
            list: All projects in the projects path.
        """
        projects_path
        os.makedirs(projects_path, exist_ok=os.X_OK)
        sub_folders = [
            name
            for name in os.listdir(projects_path)
            if os.path.isdir(os_join(projects_path, name))
        ]
        # print(sub_folders)
        return sub_folders

    def extract_node_data(
        self, elem: dict, layouts: list[str]
    ) -> list[tuple[int, int, int] and tuple[int, int, int, int]]:
        """Extracts the data from a node.

        Args:
            elem (dict): node to extract data from.
            layouts (list[str]): layouts for which data should be extracted.

        Returns:
            list[tuple[int, int, int] and tuple[int, int, int, int]]: contains coordinates (low,high) and color for each layout.
        """
        tex = []
        elem_lays = {lay[LT.name]: idx for idx, lay in enumerate(elem[NT.layouts])}
        self.extract_node_label(elem)
        for idx, layout in enumerate(layouts):
            tex.append([])
            coords = [0, 0, 0]  # x,y,z
            color = [0, 255, 255, 255]  # r,g,b,a

            if layout in elem_lays:
                l_idx = elem_lays[layout]
                lay = elem[NT.layouts][l_idx]
                position = lay[LT.position]

                if LT.color in lay:
                    if isinstance(lay[LT.color], list):
                        color = lay[LT.color]
                        if len(color) == 3:
                            color.append(255 // 2)

                for d, _ in enumerate(position):
                    coords[d] = int(float(position[d]) * 65280)

            high = [value // 255 for value in coords]
            low = [value % 255 for value in coords]

            tex[idx].append(tuple(high))
            tex[idx].append(tuple(low))
            tex[idx].append(tuple(color))

        return tex

    def extract_node_label(
        self,
        elem: dict,
    ) -> None:
        """Extracts the node labels and add them to the names dictionary.

        Args:
            elem (dict): Node from which the label should be extracted.
        """
        uniprot = elem.get(NT.name)
        if uniprot:
            name = [uniprot]
            if "names" not in self.names:
                self.names["names"] = []
            self.names["names"].append(name)

    @staticmethod
    def extract_link_data(
        elem: dict, layouts: list
    ) -> dict[str, list[tuple[int], tuple[int], tuple[int]]]:
        """Extracts the data from a node.

        Args:
            elem (dict): Link to extract data from.
            layouts (list): Layouts for which data should be extracted.

        Returns:
            list[tuple[int, int, int, int]]: contains coordinates (low,high) and color for each layout.
        """
        tex = None
        if LiT.layouts in elem.keys():
            elem_lays = {lay[LT.name]: idx for idx, lay in enumerate(elem[LiT.layouts])}
            start = int(elem[LiT.start])
            end = int(elem[LiT.end])

            sx = start % 128
            syl = start // 128 % 128
            syh = start // 16384

            ex = end % 128
            eyl = end // 128 % 128
            eyh = end // 16384
            tex = {}
            for idx, layout in enumerate(layouts):
                color = [0, 0, 0, 0]
                if layout in elem_lays:
                    layout_idx = elem_lays[layout]
                    elem_layout = elem[LiT.layouts][layout_idx]
                    if LT.color in elem_layout:
                        if isinstance(elem_layout[LT.color], tuple):
                            color = elem_layout[LT.color]
                    else:
                        color = [0, 255, 0, 255]
                    tex[layout] = [(sx, syl, syh), (ex, eyl, eyh), tuple(color)]

        return tex

    def makeNodeTex(
        self,
        nodes: dict,
        layouts: list[str] = [LT._3d],
        skip_attr: list[str] = ["layouts"],
    ) -> str:
        """Generates Node textures from a dictionary of nodes.

        Args:
            nodes (dict): contains all nodes of the network.
            layouts (list[str], optional): layouts for which the output should be generated. Defaults to [LT._3d].
            skip_attr (list[str], optional): Attributes to skip for each node . Defaults to ["layouts"].

        Returns:
            str: _description_
        """
        n = len(nodes)  # Number of Nodes
        hight = 128 * (int(n / 16384) + 1)

        size = 128 * hight
        path = self.p_path

        l_tex = []
        l_img = []
        for l in layouts:
            l_tex.append(
                [[(0, 0, 0)] * size, [(0, 0, 0)] * size, [(0, 0, 0, 0)] * size]
            )
            l_img.append(
                [
                    Image.new("RGB", (128, hight)),
                    Image.new("RGB", (128, hight)),
                    Image.new("RGBA", (128, hight)),
                ]
            )

        for _, elem in enumerate(nodes):
            elem = self.change_to_universal_attr(elem)

            self.nodes[VRNE.nodes].append(
                {k: v for k, v in elem.items() if k not in skip_attr}
            )
            tex = self.extract_node_data(elem, layouts)
            for l, _ in enumerate(layouts):
                for d in range(3):
                    l_tex[l][d][elem[NT.id]] = tex[l][d]
        output = ""

        for l, layout in enumerate(layouts):
            for d in range(3):
                l_img[l][d].putdata(l_tex[l][d])
                # new_imgl.putdata(texl)
                # new_imgc.putdata(texc)

            pathXYZ = os_join(path, "layouts", f"{layout}XYZ.bmp")
            pathXYZl = os_join(path, "layoutsl", f"{layout}XYZl.bmp")
            pathRGB = os_join(path, "layoutsRGB", f"{layout}RGB.png")
            xyz, rgb = f"{layout}XYZ", f"{layout}RGB"
            if xyz not in self.pfile["layouts"]:
                self.pfile["layouts"].append(xyz)
            if rgb not in self.pfile["layoutsRGB"]:
                self.pfile["layoutsRGB"].append(rgb)

            # if self.overwrite_project:
            l_img[l][0].save(pathXYZ)
            l_img[l][1].save(pathXYZl)
            l_img[l][2].save(pathRGB, "PNG")
            output += (
                '<br><a style="color:green;">SUCCESS </a>'
                + layout
                + " Node Textures Created"
            )
        return output

    # TODO other name for variable filename. maybe Layout name
    def makeLinkTex(self, links: dict, layouts: list) -> str:
        """Generate a Link texture from a dictionary of edges.

        Args:
            links (dict): contains all links of the network.
            layouts (list): contains all layouts for which the output should be generated.

        Returns:
            str: status message to report the status of the execution.
        """
        height = 512
        path = self.p_path

        l_tex = []
        l_img = []
        for l in layouts:
            l_tex.append([[(0, 0, 0)] * 1024 * height, [(0, 0, 0, 0)] * 512 * height])
            l_img.append(
                [Image.new("RGB", (1024, height)), Image.new("RGBA", (512, height))]
            )
        # texl = [(0, 0, 0)] * 1024 * hight
        # texc = [(0, 0, 0, 0)] * 512 * hight
        # new_imgl = Image.new("RGB", (1024, hight))
        # new_imgc = Image.new("RGBA", (512, hight))

        l_idx = [0 for _ in layouts]
        for elem in links:
            elem: dict
            link = {
                LiT.id: elem.get(LiT.id),
                LiT.start: elem.get(LiT.start),
                LiT.end: elem.get(LiT.end),
            }
            self.links[VRNE.links].append(link)
            tex = self.extract_link_data(elem, layouts)
            if tex is None:
                print("Tex is None")
                continue
            for l, layout in enumerate(layouts):
                if layout in tex:
                    idx = l_idx[l]
                    if idx >= 262144:
                        continue
                    l_tex[l][0][idx * 2] = tex[layout][0]  # texl[i * 2] = pixell1
                    l_tex[l][0][idx * 2 + 1] = tex[layout][
                        1
                    ]  # texl[i * 2 + 1] = pixell2
                    l_tex[l][1][idx] = tex[layout][2]  # texc[i] = pixelc
                    l_idx[l] += 1

        output = ""
        for l, layout in enumerate(layouts):
            l_img[l][0].putdata(l_tex[l][0])  # new_imgl.putdata(texl)
            l_img[l][1].putdata(l_tex[l][1])  # new_imgc.putdata(texc)
            pathl = os_join(path, "links", f"{layout}XYZ.bmp")
            pathRGB = os_join(path, "linksRGB", f"{layout}RGB.png")
            xyz, rgb = f"{layout}XYZ", f"{layout}RGB"
            if xyz not in self.pfile["links"]:
                self.pfile["links"].append(xyz)
            if rgb not in self.pfile["linksRGB"]:
                self.pfile["linksRGB"].append(rgb)

            # if not self.skip_exists:
            l_img[l][0].save(pathl, "PNG")
            l_img[l][1].save(pathRGB, "PNG")
            output += (
                '<br><a style="color:green;">SUCCESS </a>'
                + layout
                + " Link Textures Created"
            )
            # else:
            #     if os.path.exists(pathl):
            #         output += (
            #             '<a style="color:red;">ERROR </a>'
            #             + layout
            #             + " linklist already in project"
            #         )
            #     else:
            #         l_img[l][0].save(pathl, "PNG")
            #         l_img[l][0].save(pathRGB, "PNG")
            #         output += (
            #             '<a style="color:green;">SUCCESS </a>'
            #             + layout
            #             + " Link Textures Created"
            #         )

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
            if f"{LT.cy_layout}XYZ" not in self.pfile[PT.layouts]:
                self.pfile[PT.layouts] = [
                    f"{LT.string_3d_no_z}XYZ",
                    f"{LT.string_3d}XYZ",
                ]
                self.pfile[PT.layouts_rgb] = [
                    f"{LT.string_3d_no_z}RGB",
                    f"{LT.string_3d}RGB",
                ]
        log.debug("Project stringifyed")

        with open(self.pfile_file, "w") as json_file:
            json.dump(self.pfile, json_file)

    def extract_nodes(self, nodes, skip_attr, layouts):
        for _, elem in enumerate(nodes):
            elem = self.change_to_universal_attr(elem)

            self.nodes[VRNE.nodes].append(
                {k: v for k, v in elem.items() if k not in skip_attr}
            )
            tex = self.extract_node_data(elem, layouts)
            for l, _ in enumerate(layouts):
                for d in range(3):
                    l_tex[l][d][elem[NT.id]] = tex[l][d]

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
        prolist = self.listProjects(self.pf_path)

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

        state += self.makeNodeTex(nodes, layouts=n_lay)

        state += self.makeLinkTex(links, l_lay)

        self.write_json_files()

        try:
            GD.sessionData["proj"] = self.listProjects(self.pf_path)
        except NameError:
            pass

        return state

    def change_to_universal_attr(self, node: dict) -> dict:
        """Rename STRING DB attributes to vrnetzer universal attributes so they will be displayed at the correct place on the node panel

        Args:
            node (dict): Node to change.

        Returns:
            dict: Node with changed attribute keys.
        """
        universal_attributes = [NT.description, NT.sequence, NT.species]
        string_attributes = [
            ST.stringdb_description,
            ST.stringdb_sequence,
            ST.stringdb_species,
        ]
        for u_att, s_attr in zip(universal_attributes, string_attributes):
            if s_attr in node:
                node[u_att] = node[s_attr]
                del node[s_attr]
        return node

    def color_nodes(
        self,
        target_project: str,
        new_nodes: dict[str, dict],
        mapping_color: list[int, int, int] = _MAPPING_ARBITARY_COLOR,
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

        self.makeLinkTex(links, l_lay)
        self.stringify_project(nodes=False)

        self.pfile[PT.links] += [
            link for link in target_links if "stringdb" not in link
        ]
        self.pfile[PT.links_rgb] += [
            link for link in target_links_rgb if "stringdb" not in link
        ]

        self.nodes = {"nodes": []}  # Reset nodes
        for elem in self.network[VRNE.nodes]:
            elem = self.change_to_universal_attr(elem)
            self.nodes[VRNE.nodes].append(
                {k: v for k, v in elem.items() if k not in ["layouts"]}
            )
        with open(self.links_file, "r") as json_file:
            self.links = json.load(json_file)

        self.write_json_files()
        for l, layout in enumerate(layouts):
            pathRGB = os_join(target_project, "layoutsRGB", f"{layout}.png")
            img = Image.open(pathRGB)
            i = 0
            all_nodes_done = False
            for y in range(img.width):
                for x in range(img.height):
                    if i >= len(self.network["nodes"]):
                        all_nodes_done = True
                        break
                    node = self.network["nodes"][i]
                    if node[NT.node_color] == mapping_color:
                        color = node[NT.node_color] + [50]
                    else:
                        color = node[NT.node_color] + [255 // 2]
                    img.putpixel((x, y), tuple(color))
                    i += 1
                if all_nodes_done:
                    break

            img.save(os_join(self.p_path, "layoutsRGB", f"{layout}.png"))
