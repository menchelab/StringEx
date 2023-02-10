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
from src.classes import Organisms
import interactomes.arg_parser as arg_parser

st.log = logger.get_logger(
    name="interactome_construction",
    level=st._LOG_LEVEL,
    f_level=st.F_LOG_LEVEL,
    c_level=st.C_LOG_LEVEL,
    format=st._LOG_FORMAT,
    c_format=st._LOG_FORMAT,
    log_file="interactome_construction.log",
    runtimes_files="interactome_construction_runtimes.log",
)

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
            if parser.opt_dist:
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
                if isinstance(parser.layout_algo, str):
                    parser.layout_algo = [parser.layout_algo]
                read_string.construct_layouts(
                    clean_name,
                    parser.src_dir,
                    parser.layout_algo,
                    variables,
                    parser.overwrite,
                    parser.overwrite_links,
                    parser.threshold,
                    parser.max_links,
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
        # "spring",
        # "cg_global_umap",
        # "cg_global_tsne",
        # "cg_local_umap",
        # "cg_local_tsne",
        "cg_importance_umap"
    ]
    parser.organism.remove("reproduce")
    if parser.organism == "all" or len(parser.organism) == 0:
        parser.organism = Organisms.all_organisms
        parser.organism.remove("D.melanogaster")
    flag = " ".join(
        [
            handle
            for f, handle in zip(
                [parser.overwrite, parser.overwrite_links], ["-ow", "-owl"]
            )
            if f
        ]
    )
    # Download and construct graphs for all organisms
    for organism in parser.organism:
        base = ["-lu", organism, "-b"]
        if flag:
            base += flag.split(" ")
        if not parser.download:
            base[0] += "d"
        if not parser.construct:
            base[0] += "c"
        st.log.debug(base)
        main(base)
    base += ["-lay"]
    # calculate all respective layouts for the organisms
    for organism in parser.organism:
        base[1] = organism
        disabled = "-"
        if not parser.download:
            disabled += "d"
        if not parser.construct:
            disabled += "c"
        if not parser.layout:
            disabled += "l"
        if "u" not in disabled:
            disabled += "u"
        for algo in parser.layout_algo:
            if "c" not in disabled:
                disabled += "c"
            if "d" not in disabled:
                disabled += "d"
            args = [disabled] + base[1:] + [algo]
            for k, v in variables[organism][algo].items():
                args += [f"{k}", f"{v}"]
            st.log.debug(args)
            main(args)
    if parser.upload:
        args = (
            ["-dcl"]
            + base[2:-1]
            + parser.organism
            + ["-p", f"{parser.port}", "-ip", f"{parser.ip}"]
        )
        st.log.debug(args)
        main(args)


def main(args=None):
    """Main function to construct the node layout and link layout files which can be uploaded to the VRNetzer website. This is to reproduce the full interactome STRING networks from scratch. If benchmark is on it will benchmark the runtime of the different steps."""
    parser = arg_parser.parse_args(args)
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
