#!Python3
import argparse
import json
import os
import timeit
from datetime import timedelta

import interactomes.load_files as load_files
import interactomes.read_string as read_string
import interactomes.upload_network as upload_network
import src.logger as logger
import src.settings as st
from src.classes import LayoutAlgroithms, Organisms

st.log = logger.get_logger(
    "interactome_construction",
    level=st._LOG_LEVEL,
    f_level=st.F_LOG_LEVEL,
    c_level=st.C_LOG_LEVEL,
    format=st._LOG_FORMAT,
    log_file="interactome_construction.log",
    runtimes_files="interactome_construction_runtimes.log",
)
_SOURCE_FILES = os.path.join(".", "string_interactomes")
_OUTPUT_PATH = os.path.join(".", "csv", "string_interactomes")


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
    # TODO: Ask christ about the parameters
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
        "-st",
        type=int,
        help="Step parameter of cartoGRAPHs local algorithms.",
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
        default=264144,
    )
    if args is None:
        return parser.parse_args()
    return parser.parse_args(args)


def workflow(parser):
    runtimes = {}
    for organism in parser.organism:
        if parser.benchmark:
            start_time = timeit.default_timer()
            runtimes[organism] = {}
        tax_id = Organisms.get_tax_ids(organism)
        clean_name = Organisms.get_file_name(organism)
        st.log.info(f"Processing organism: {organism} with taxonomy id: {tax_id}.")

        if parser.download:

            def download():
                load_files.download(tax_id, parser.src_dir, clean_name)

            if parser.benchmark:
                download_runtime = timeit.repeat(
                    download,
                    repeat=parser.benchmark_repeat,
                    number=parser.benchmark_number,
                )
                average = sum(download_runtime) / len(download_runtime)
                download_runtime = str(timedelta(seconds=average))
                st.log.info(f"Runtime of step download: {download_runtime}")
                runtimes[organism]["download"] = download_runtime
            else:
                download()

        if parser.construct:

            def construct():
                read_string.construct_graph(
                    parser.src_dir,
                    organism,
                    clean_name,
                    tax_id,
                    parser.last_link,
                    parser.max_links,
                )

            if parser.benchmark:
                construct_runtime = timeit.repeat(
                    construct,
                    repeat=parser.benchmark_repeat,
                    number=parser.benchmark_number,
                )
                average = sum(construct_runtime) / len(construct_runtime)
                construct_runtime = str(timedelta(seconds=average))
                st.log.info(f"Runtime of step construct: {construct_runtime}")
                runtimes[organism]["construct"] = construct_runtime
            else:
                construct()

        if parser.layout:
            if parser.opt_dist <= 0:
                parser.opt_dist = None
            variables = {
                "prplxty": parser.prplxty,
                "density": parser.density,
                "l_rate": parser.lrate,
                "steps": parser.steps,
                "n_neighbors": parser.n_neighbors,
                "spread": parser.spread,
                "min_dist": parser.min_dist,
                "opt_dist": parser.opt_dist,
                "iterations": parser.iterations,
                "threshold": parser.spring_threshold,
            }

            def layout():
                if isinstance(parser.layout_algo,str):
                    parser.layout_algo = [parser.layout_algo]
                read_string.construct_layouts(
                    clean_name,
                    parser.src_dir,
                    parser.layout_algo,
                    variables,
                    parser.overwrite,
                    parser.overwrite_links,
                )

            if parser.benchmark:
                layout_runtime = timeit.repeat(
                    layout,
                    repeat=parser.benchmark_repeat,
                    number=parser.benchmark_number,
                )
                average = sum(layout_runtime) / len(layout_runtime)
                layout_runtime = str(timedelta(seconds=average))
                st.log.info(f"Runtime of step layout: {layout_runtime}")
                runtimes[organism]["layout"] = layout_runtime
            else:
                layout()

        ##### Irrelevant for runtime, can ignore
        if parser.upload:

            def upload():
                upload_network.upload(
                    clean_name,
                    parser.src_dir,
                    parser.ip,
                    parser.port,
                )

            if parser.benchmark:
                upload_runtime = timeit.repeat(
                    upload,
                    repeat=parser.benchmark_repeat,
                    number=parser.benchmark_number,
                )
                average = sum(upload_runtime) / len(upload_runtime)
                upload_runtime = str(timedelta(seconds=average))
                st.log.info(f"Runtime of step upload: {upload_runtime}")
                runtimes[organism]["upload"] = upload_runtime
            else:
                upload()
        if parser.benchmark:
            runtimes[organism]["total"] = timedelta(
                seconds=timeit.default_timer() - start_time
            )
    return runtimes


def reproduce_networks(parser: argparse.Namespace) -> None:
    """This will reproduce all the interactomes StringEX from source with the same parameters as in th original paper."""
    variables_file = os.path.join(
        os.path.abspath(os.path.dirname(__file__)), "interactomes", "variables.json"
    )
    with open(variables_file) as f:
        variables = json.load(f)

    parser.layout_algo = [
        "spring",
        "cg_global_umap",
        "cg_global_tsne",
        "cg_local_umap",
        "cg_local_tsne",
    ]
    parser.organism.remove("reproduce")
    if parser.organism == "all":
        parser.organism = Organisms.all_organisms
    for organism in parser.organism:
        algo = parser.layout_algo[0]
        disabled = "-"
        if not parser.download:
            disabled += "d"
        if not parser.construct:
            disabled += "c"
        if not parser.layout:
            disabled += "l"
        if "u" not in disabled:
            disabled += "u"
        base = [
            disabled,
            organism,
            "-b",
            "-lay",
        ]
        for idx, algo in enumerate(parser.layout_algo):
            if idx == 0:
                args = base + [algo]
            else:
                if "c" not in disabled:
                    disabled += "c"
                if "d" not in disabled:
                    disabled += "d"
                args = [disabled] + base[1:] + [algo]
            for k, v in variables[organism][algo].items():
                args += [f"{k}", f"{v}"]
            main(args)
    args = ["-dcl", "all", "-p", f"{parser.port}", "-ip", f"{parser.ip}"]
    main(args)


def main(args=None):
    """Main function to construct the node layout and link layout files which can be uploaded to the VRNetzer website. This is to reproduce the full interactome STRING networks from scratch. If benchmark is on it will benchmark the runtime of the different steps."""
    parser = parse_args(args)
    if "reproduce" in parser.organism:
        reproduce_networks(parser)
        return
    if "all" in parser.organism:
        parser.organism = Organisms.all_organisms
    if parser.benchmark:
        total_runtime = timeit.default_timer()
        runtimes = workflow(parser)
        total_runtime = timedelta(seconds=timeit.default_timer() - total_runtime)
        st.log.info(f"Overall runtime for: \t\t\t\t{total_runtime}")
        st.log.info(f"=" * 50)
        for organism, r in runtimes.items():
            total_runtime = r.pop("total")
            st.log.info(f"Total runtime for {organism}: \t\t\t\t{total_runtime}")
            st.log.info(f"=" * 50)
            for step, runtime in r.items():
                if runtime:
                    st.log.info(f"Runtime of step {step}: \t{runtime}")
    else:
        workflow(parser)


if __name__ == "__main__":
    main()
