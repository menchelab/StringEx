try:
    from pip._internal.operations import freeze
except ImportError:  # pip < 10.0
    from pip.operations import freeze

import sys
from enum import Enum


# Tags
class LayoutTags:
    """
    This class provides access to the tags which are used in the layout section
    of a VRNetz file.
    """

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
    """
    This class provides access to the tags which are used in the node section of
    a VRNetz file.
    """

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
    size = "size"
    gene_name = "gene_name"
    short = "short"


class StringTags:
    """
    This class provides access to the tags which are used by stringdb networks
    in Cytoscape.
    """

    stringdb_canoncial_name = "stringdb_canonical name"
    stringdb_sequence = "stringdb_sequence"
    stringdb_description = "stringdb_description"
    stringdb_species = "stringdb_species"
    stringdb_shared_name = "shared name"
    stringdb_score = "stringdb_score"
    stringdb_identifier = "stringdb_database identifier"


class CytoscapeTags:
    """
    This class provides access to the tags which are used by Cytoscape.
    """

    name = "name"
    shared_name = "shared name"
    suid = "SUID"


class ProjectTag:
    """
    This class provides access to the layouts keys of a pfile.
    """

    layouts = "layouts"
    layouts_rgb = "layoutsRGB"
    links = "links"
    links_rgb = "linksRGB"


class LinkTags:
    """
    This class provides access to the tags which are used in the link section of
    a VRNetz file.
    """

    id = "id"
    start = "s"
    end = "e"
    suid = "SUID"
    ppi_id = "ppi_id"
    layouts = "c"


class VRNetzElements:
    """
    This class provides access to the keys of a VRNetz file.
    """

    nodes = "nodes"
    links = "links"
    node_layouts = "layouts"  # edge layout
    link_layouts = "l_layout"  # link layout
    network = "network"


class LayoutAlgorithms:
    """
    This class provides access to all available layout algorithms.
    """

    spring = "spring"
    kamada_kawai = "kamada_kawai"
    all_algos = [spring, kamada_kawai]
    random = "random"
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
    """
    This class provides access to all available evidence of a string network.
    """

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
        """
        Return a list of all evidences.

        Returns:
            list[str]: List of all evidences.
        """

        return [e.value for e in Evidences]

    @staticmethod
    def get_all_evidences_except_any() -> list[str]:
        """
        Return a list of all evidences except any.

        Returns:
            list[str]: List of all evidences except any.
        """
        return [e.value for e in Evidences if e != Evidences.any]

    @staticmethod
    def get_default_scheme() -> dict:
        """
        Return a dictionary with the color scheme for each evidence.

        Returns:
            dict[str,tuple[int,int,int,int]]: keys are the evidences and values
            are the RGBA.
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
    """
    This class consolidates scientific names of organisms, their tax ids and
    their directories used for the interactome creation.
    """

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
    def get_tax_ids(organism: str = None, directory: str = None) -> int:
        """Return the tax id for the organism.

        Args:
            organism (str): organism for which the tax id is needed

        Returns:
            int: taxanomy id of the organism
        """
        if organism:
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

        if directory:
            tax_ids = {
                "string_human_ppi": 9606,
                "string_mouse_ppi": 10090,
                "string_rat_ppi": 10116,
                "string_zebrafish_ppi": 7955,
                "string_fly_ppi": 7227,
                "string_worm_ppi": 6239,
                "string_yeast_ppi": 4932,
                "string_ecoli_ppi": 362663,
                "string_arabidopsis_ppi": 3702,
            }
            return tax_ids.get(directory)

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
        """Return the project name for the desired organism. The Organism has to be given as the scientific name. For example: "Homo sapiens". Or use Organisms.human.

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

    def get_organism_name(directory: str = None, tax_id: int = None) -> str:
        """Get the scientific name of the organism from the directory or the tax id.

        Args:
            directory (str, optional): directory name in which the organism data is stored. Defaults to None.
            tax_id (int, optional): Tax id of the respective organism. Defaults to None.

        Raises:
            ValueError: If no directory or tax id is provided.

        Returns:
            str: Scientific name of the organism.
        """
        if directory is None and tax_id is None:
            raise ValueError("You must provide a directory or a tax id")
        if directory:
            organism_names = {
                "string_human_ppi": Organisms.human,
                "string_mouse_ppi": Organisms.mouse,
                "string_yeast_ppi": Organisms.yeast,
                "string_worm_ppi": Organisms.worm,
                "string_fly_ppi": Organisms.fly,
                "string_arabidopsis_ppi": Organisms.arabidopsis,
                "string_zebrafish_ppi": Organisms.zebrafish,
                "string_rat_ppi": Organisms.rat,
                "string_ecoli_ppi": Organisms.ecoli,
            }
            return organism_names.get(directory)
        if tax_id:
            organism_names = {
                9606: Organisms.human,
                10090: Organisms.mouse,
                4932: Organisms.yeast,
                6239: Organisms.worm,
                7227: Organisms.fly,
                3702: Organisms.arabidopsis,
                7955: Organisms.zebrafish,
                10116: Organisms.rat,
                362663: Organisms.ecoli,
            }
            return organism_names.get(tax_id)
