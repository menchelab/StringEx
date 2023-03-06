import argparse
import os

from src import settings as st
from src.classes import LayoutAlgroithms, Organisms

_SOURCE_FILES = os.path.join(".", "string_interactomes")
_OUTPUT_PATH = os.path.join(".", "csv", "string_interactomes")


def range_limited_functional_threshold(arg):
    """Type function for argparse - a float within some predefined bounds"""
    try:
        f = float(arg)
    except ValueError:
        raise argparse.ArgumentTypeError("Must be a floating point number")
    if f < 0.01 or f > 1:
        raise argparse.ArgumentTypeError(
            "Argument must be < " + str(0.1) + "and > " + str(1)
        )
    return f


def parse_args(args=None):
    parser = argparse.ArgumentParser(description="Construct STRING interactomes")
    organisms = Organisms.all_organisms.copy()
    organisms.extend(["reproduce", "all"])
    parser.add_argument(
        "organism",
        type=str,
        help="Organism to construct the interactome for.",
        choices=organisms,
        nargs="*",
    )
    parser.add_argument(
        "--download",
        "-d",
        action="store_false",
        help="Download the interactome files from the STRING website.",
    )
    parser.add_argument(
        "--construct",
        "-c",
        action="store_false",
        help="Construct the interactome files from the downloaded files.",
    )
    parser.add_argument(
        "--layout",
        "-l",
        action="store_false",
        help="Construct the node and link layout files from the interactome files.",
    )
    parser.add_argument(
        "--upload",
        "-u",
        action="store_false",
        help="Upload the node and link layout files to the VRNetzer website.",
    )
    parser.add_argument(
        "-ip", type=str, help="IP address of the VRNetzer website.", default="localhost"
    )
    parser.add_argument(
        "--port", "-p", type=int, help="Port of the VRNetzer website.", default=5000
    )
    # parser.add_argument(
    #     "--tarball",
    #     "-tar",
    #     type=str,
    #     help="Path to the directory where the tarball can be found.",
    #     default=_SOURCE_FILES,
    # )
    parser.add_argument(
        "-output_dir",
        "-out",
        type=str,
        help="Path to the output directory where the interactome files should be stored.",
        default=_OUTPUT_PATH,
    )
    parser.add_argument(
        "--src_dir",
        "-src",
        type=str,
        help="Path to the directory where the interactome files are stored.",
        default=_SOURCE_FILES,
    )
    parser.add_argument(
        "--layout_algo",
        "-lay",
        type=str,
        help="Defines the layout algorithm which should be used.",
        nargs="*",
        default=LayoutAlgroithms.spring,
        choices=LayoutAlgroithms.all_algos,
    )
    parser.add_argument(
        "--overwrite",
        "-ow",
        action="store_true",
        default=False,
        help="Turns on to overwrite <layout>_nodes.csv layout files.",
    )
    parser.add_argument(
        "--overwrite_links",
        "-owl",
        action="store_true",
        default=False,
        help="Turns on to overwrite <layout>_links.csv layout files.",
    )
    parser.add_argument(
        "--layout_threshold",
        "-lay_thr",
        type=float,
        help="Defines the score a link must have to be included for link based layout calculations.",
        default=0.4,
    )
    parser.add_argument(
        "--layout_name",
        "-name",
        type=str,
        help="Defines the name of the layout files.",
        nargs="*",
    )
    parser.add_argument(
        "--feature_matrices",
        "-fm",
        action="store_true",
        help="Constructs the feature matrices and only the feature matrices for all proteins in STRING.",
        default=False,
    )
    parser.add_argument(
        "--plot_feature_matrices",
        "-pltfm",
        action="store_true",
        help="Plots the feature matrices distribution.",
        default=False,
    )
    parser.add_argument(
        "--n_processes",
        "-np",
        type=int,
        help="Defines the number of processes to for layout calculations and upload",
        default=os.cpu_count() - 1,
    )
    parser.add_argument(
        "--parallel",
        "-par",
        action="store_true",
        help="Turns on parallel processing for layout calculations and upload",
        default=False,
    )
    parser.add_argument(
        "--recolor",
        "-rec",
        action="store_true",
        help="Allows to just recolor the nodes based on the layout files.",
    )
    ### CARTOGRAPH VARIABLES ###
    ### TSNE ###
    parser.add_argument(
        "--prplxty",
        "-prp",
        type=int,
        help="Perplexity parameter of cartoGRAPHs TSNE algorithms.",
        default=50,
    )
    parser.add_argument(
        "--density",
        "-den",
        type=int,
        help="Density parameter of cartoGRAPHs TSNE algorithms.",
        default=12,
    )
    parser.add_argument(
        "--lrate",
        "-lra",
        type=int,
        help="l_rate parameter of cartoGRAPHs tsne algorithms.",
        default=200,
    )
    parser.add_argument(
        "--steps",
        "-ste",
        type=int,
        help="Step parameter of cartoGRAPHs tsne algorithms.",
        default=250,
    )
    ### UMAP ###
    parser.add_argument(
        "--n_neighbors",
        "-nn",
        type=int,
        help="Defines the number of neighbor parameter of cartoGRAPHs umap algorithms.",
        default=10,
    )
    parser.add_argument(
        "--spread",
        "-spr",
        type=float,
        help="Defines the spread parameter of cartoGRAPHs umap algorithms.",
        default=1.0,
    )
    parser.add_argument(
        "--min_dist",
        "-md",
        type=float,
        help="Defines the min_dist parameter of cartoGRAPHs umap algorithms.",
        default=0.1,
    )
    ### Functional Layouts ###
    parser.add_argument(
        "--max_num_features",
        "-maxf",
        type=int,
        help="Defines the maximum number of features to be used for the functional layouts.",
        default=30,
    )
    parser.add_argument(
        "--functional_threshold",
        "-fthr",
        type=range_limited_functional_threshold,
        help="Defines the percentage of nodes that have to be annotated with a feature to be used for the functional layouts.",
        default=0.05,
    )
    parser.add_argument(
        "--max_num_annotations",
        "-maxa",
        type=int,
        help="Defines the maximum number of annotations to be added to the node annotations.",
        default=30,
    )
    parser.add_argument(
        "--annotation_threshold",
        "-athr",
        type=range_limited_functional_threshold,
        help="Defines the percentage of nodes that have to be annotated with a feature to be added to the node annotations.",
        default=0.1,
    )
    parser.add_argument(
        "--epsilon",
        "-eps",
        type=float,
        help="Defines the epsilon parameter of the HDBSCAN algorithm.",
        default=None,
    )
    ### SPRING VARIABLES ###
    parser.add_argument(
        "--opt_dist",
        "-opd",
        type=float,
        help="Defines the optimal distance parameter k of NetworkX's spring algorithm.",
        default=0,
    )
    parser.add_argument(
        "--iterations",
        "-it",
        type=int,
        help="Defines the number of iterations parameter of NetworkX's spring algorithm.",
        default=50,
    )
    parser.add_argument(
        "--spring_threshold",
        "-spth",
        type=float,
        help="Defines the threshold parameter of NetworkX's spring algorithm.",
        default=0.0001,
    )
    # Benchmark
    parser.add_argument(
        "--benchmark",
        "-b",
        action="store_true",
        help="Benchmark the runtime of the different steps.",
    )
    parser.add_argument(
        "--benchmark_repeat",
        "-br",
        type=int,
        help="Number of times the benchmark should be repeated.",
        default=1,
    )
    parser.add_argument(
        "--benchmark_number",
        "-bn",
        type=int,
        help="Number of executions per repeat to benchmark.",
        default=1,
    )
    # Debug
    parser.add_argument(
        "--last_link",
        "-ll",
        type=int,
        help="Stop constructing at this link.",
        default=None,
    )
    parser.add_argument(
        "--max_links",
        "-ml",
        type=int,
        help="Filter out every links that is more than this based on experimental score and combined score.",
        default=st.MAX_NUM_LINKS,
    )
    parser.add_argument(
        "--no_lay",
        "-nl",
        action="store_true",
        help="Turns off the layout construction.",
    )
    parser.add_argument(
        "--preview_layout",
        "-pl",
        action="store_true",
        help="Visualizes the colored layout in a preview window.",
    )
    parser.add_argument(
        "--no_upload",
        "-nu",
        action="store_true",
        help="Wont upload the network again only change meta data.",
        default=False,
    )
    if args is None:
        return parser.parse_args()
    return parser.parse_args(args)
