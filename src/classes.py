try:
    from pip._internal.operations import freeze
except ImportError:  # pip < 10.0
    from pip.operations import freeze

import sys
from enum import Enum


# Tags
class LayoutTags:
    position = "p"
    color = "c"
    size = "s"
    id = "id"
    cy_layout = "cy"
    name = "n"
    _3d = "3d"
    string_3d = "3d"
    string_3d_no_z = "2d"


class NodeTags:
    layouts = "layouts"
    vrnetzer_pos = "vp"
    node_color = "c"
    name = "n"
    suid = "SUID"
    description = "description"
    sequence = "sequence"
    species = "species"
    ppi_id = "ppi_id"
    id = "id"
    attr_lst = "attrlist"
    uniprot = "uniprot"
    display_name = "display name"


class StringTags:
    stringdb_canoncial_name = "stringdb_canonical name"
    stringdb_sequence = "stringdb_sequence"
    stringdb_description = "stringdb_description"
    stringdb_species = "stringdb_species"
    stringdb_shared_name = "shared name"
    stringdb_score = "stringdb_score"


class ProjectTag:
    layouts = "layouts"
    layouts_rgb = "layoutsRGB"
    links = "links"
    links_rgb = "linksRGB"


class AttrTags:
    names = "names"


class LinkTags:
    id = "id"
    start = "s"
    end = "e"
    suid = "SUID"
    ppi_id = "ppi_id"
    layouts = "c"


class VRNetzElements:
    nodes = "nodes"
    links = "links"
    node_layouts = "layouts"  # edge layout
    link_layouts = "l_layout"  # link layout
    network = "network"


class LayoutAlgroithms:
    spring = "spring"

    kamada_kawai = "kamada_kawai"
    all_algos = [spring, kamada_kawai]
    cartoGRAPH = "cg"
    cartoGRAPH_local = "local"
    cartoGRAPH_global = "global"
    cartoGRAPH_importance = "importance"
    cartoGRAPH_tsne = "tsne"
    cartoGRAPH_umap = "umap"
    cartoGRAPH_functional = "functional"

    if "cartoGRAPHs" in [module.split("=")[0] for module in list(freeze.freeze())]:
        all_algos += [
            f"{cartoGRAPH}_{cartoGRAPH_local}_{cartoGRAPH_tsne}",
            f"{cartoGRAPH}_{cartoGRAPH_local}_{cartoGRAPH_umap}",
            f"{cartoGRAPH}_{cartoGRAPH_global}_{cartoGRAPH_tsne}",
            f"{cartoGRAPH}_{cartoGRAPH_global}_{cartoGRAPH_umap}",
            f"{cartoGRAPH}_{cartoGRAPH_importance}_{cartoGRAPH_tsne}",
            f"{cartoGRAPH}_{cartoGRAPH_importance}_{cartoGRAPH_umap}",
            f"{cartoGRAPH}_{cartoGRAPH_functional}_{cartoGRAPH_umap}",
        ]


class Evidences(Enum):
    any = "any"
    stringdb_textmining = "stringdb_textmining"
    stringdb_experiments = "stringdb_experiments"
    stringdb_coexpression = "stringdb_coexpression"
    stringdb_databases = "stringdb_databases"
    stringdb_neighborhood = "stringdb_neighborhood"
    stringdb_cooccurrence = "stringdb_cooccurrence"
    stringdb_fusion = "stringdb_fusion"
    stringdb_similarity = "stringdb_similarity"

    @staticmethod
    def get_all_evidences() -> list[str]:
        return [e.value for e in Evidences]

    @staticmethod
    def get_all_evidences_except_any() -> list[str]:
        return [e.value for e in Evidences if e != Evidences.any]

    @staticmethod
    def get_default_scheme() -> dict:
        """Return a dictionary with the color scheme for each evidence.

        Returns:
            dict[str,tuple[int,int,int,int]]: keys are the evidences and values are the RGBA.
        """
        ev = {
            Evidences.any.value: (
                200,
                200,
                200,
                255,
            ),  # Color for all evidences active #c8c8c8
            Evidences.stringdb_textmining.value: (199, 234, 70, 255),  # #c6ea46
            # "stringdb_interspecies": (125, 225, 240, 255), # Not Used anywhere
            Evidences.stringdb_experiments.value: (254, 0, 255, 255),  # ##ff00ff
            Evidences.stringdb_coexpression.value: (50, 50, 50, 255),  # #323232
            Evidences.stringdb_databases.value: (0, 255, 255, 255),  # #00ffff
            Evidences.stringdb_neighborhood.value: (0, 255, 0, 255),  # #00ff00
            Evidences.stringdb_cooccurrence.value: (0, 0, 255, 255),  # #0000ff
            Evidences.stringdb_fusion.value: (255, 0, 0, 255),  # #ff0000
            Evidences.stringdb_similarity.value: (157, 157, 248, 255),  # #9d9df8
        }
        return ev


class Organisms:
    human = "H.sapiens"
    mouse = "M.musculus"
    yeast = "S.cerevisiae"
    worm = "C.elegans"
    fly = "D.melanogaster"
    arabidopsis = "A.thaliana"
    zebrafish = "D.rerio"
    rat = "R.norvegicus"
    ecoli = "E.coli"
    all_organisms = sorted(
        [human, mouse, yeast, worm, fly, arabidopsis, zebrafish, rat, ecoli]
    )

    @staticmethod
    def get_tax_ids(organism: str) -> int:
        """Return the tax id for the organism.

        Args:
            organism (str): organism for which the tax id is needed

        Returns:
            int: taxanomy id of the organism
        """
        tax_ids = {
            Organisms.human: 9606,
            Organisms.mouse: 10090,
            Organisms.rat: 10116,
            Organisms.zebrafish: 7955,
            Organisms.fly: 7227,
            Organisms.worm: 6239,
            Organisms.yeast: 4932,
            Organisms.ecoli: 362663,
            Organisms.arabidopsis: 3702,
        }
        return tax_ids.get(organism)

    @staticmethod
    def get_scientific_name(organism: str) -> str:
        """Return the tax id for the organism.

        Args:
            organism (str): organism for which the scientific name is needed

        Returns:
            str: Scientific name of the organism.
        """
        tax_ids = {
            Organisms.human: "Homo sapiens",
            Organisms.mouse: "Mus musculus",
            Organisms.rat: "Rattus norvegicus",
            Organisms.zebrafish: "Danio rerio",
            Organisms.fly: "Drosophila melanogaster",
            Organisms.worm: "Caenorhabditis elegans",
            Organisms.yeast: "Saccharomyces cerevisiae",
            Organisms.ecoli: "Escherichia coli 536",
            Organisms.arabidopsis: "Arabidopsis thaliana",
        }
        return tax_ids.get(organism)

    @staticmethod
    def get_file_name(organism: str) -> str:
        """Return the project name for the desired organism.

        Args:
            organism (str): organism for which the project name is needed

        Returns:
            str: name of the project
        """
        file_names = {
            Organisms.human: "string_human_ppi",
            Organisms.mouse: "string_mouse_ppi",
            Organisms.yeast: "string_yeast_ppi",
            Organisms.worm: "string_worm_ppi",
            Organisms.fly: "string_fly_ppi",
            Organisms.arabidopsis: "string_arabidopsis_ppi",
            Organisms.zebrafish: "string_zebrafish_ppi",
            Organisms.rat: "string_rat_ppi",
            Organisms.ecoli: "string_ecoli_ppi",
        }
        return file_names.get(organism)
