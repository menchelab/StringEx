#!Python3
import argparse
import json
import yaml
import os
import timeit
from datetime import timedelta

from interactomes import arg_parser
from interactomes import load_files
from interactomes import construct_network
from interactomes import upload_network
from interactomes import check_feature_matrices as feature_matrices
from interactomes import util

import src.logger as logger
import src.settings as st
from src.classes import Organisms, LayoutAlgorithms
import multiprocessing as mp

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
        if parser.recolor:
            util.recolor(
                parser.src_dir,
                clean_name,
                organism,
                tax_id,
                parser.functional_threshold,
                parser.epsilon,
                parser.preview_layout,
                parser.layout_threshold,
            )
            return

        if parser.feature_matrices or parser.plot_feature_matrices:

            fm_runtimes = feature_matrices.main(parser, clean_name)
            if fm_runtimes:
                runtimes[organism].update(fm_runtimes)
                if "construct_fm" in fm_runtimes:
                    st.log.info(
                        f"Runtime of step construct_fm: {fm_runtimes['construct_fm']}"
                    )
                if "plot_fm" in fm_runtimes:
                    st.log.info(f"Runtime of step plot_fm: {fm_runtimes['plot_fm']}")
            return

        if parser.download:

            def download():
                load_files.download(tax_id, parser.src_dir, clean_name)
                load_files.gene_ontology_download(organism, parser.src_dir, clean_name)
                load_files.download_go_terms(parser.src_dir)
                load_files.download_uniprot_keywords(parser.src_dir)

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
                construct_network.construct_graph(
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
                if parser.layout_algo is None:
                    parser.layout_algo = LayoutAlgorithms.spring
                if isinstance(parser.layout_algo, str):
                    parser.layout_algo = [parser.layout_algo]
                construct_network.construct_layouts(
                    clean_name,
                    parser.src_dir,
                    parser.layout_algo,
                    variables,
                    parser.overwrite,
                    parser.overwrite_links,
                    parser.layout_threshold,
                    parser.epsilon,
                    parser.max_links,
                    parser.layout_name,
                    parser.max_num_features,
                    parser.functional_threshold,
                    parser.no_lay,
                    parser.preview_layout,
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
                    parser.annotation_threshold,
                    parser.max_num_annotations,
                    parser.no_upload,
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
        os.path.abspath(os.path.dirname(__file__)), "interactomes", "variables.yaml"
    )
    with open(variables_file) as f:
        variables = yaml.safe_load(f)
    parser.organism.remove("reproduce")
    if parser.organism == "all" or len(parser.organism) == 0:
        parser.organism = Organisms.all_organisms
    n = len(parser.organism)
    np = parser.n_processes
    parallelize = False
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
        base = ["-lu", organism]
        if flag:
            base += flag.split(" ")
        if not parser.download:
            base[0] += "d"
        if not parser.construct:
            base[0] += "c"
        st.log.debug(base)
        main(base)
    # calculate all respective layouts for the organisms
    if parser.no_lay:
        base += ["-nl"]
    if parser.preview_layout:
        base += ["-pl"]
    base += ["-lay"]

    algo_variables = variables["default_layout"]
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
        m = len(algo_variables)
        if m > 1 and parser.parallel:
            parallelize = True
            if m > np:
                m = np
            pool = mp.Pool(m)
        else:
            parallelize = False

        arguments = []
        algos = [key for key, v in algo_variables.items()]
        if parser.layout_algo:
            algos = parser.layout_algo

        # Overwrite if for the respective organism as specific set of parameters is given
        for key in variables:
            if organism in key:
                for algo in algo_variables:
                    if algo in variables[key]:
                        algo_variables[algo].update(variables[key][algo])
                break

        for algo, var in algo_variables.items():
            if algo not in algos:
                continue
            st.log.info(f"Calculating layout for {organism} with {algo} algorithm")
            if "c" not in disabled:
                disabled += "c"
            if "d" not in disabled:
                disabled += "d"
            args = [disabled] + base[1:] + [algo]
            for k, v in var.items():
                if k not in args:
                    args += [f"{k}", f"{v}"]
            st.log.debug(args)
            arguments.append(args)

        if parallelize:
            pool.map_async(main, arguments)
            pool.close()
            pool.join()
        else:
            for arg in arguments:
                main(arg)

    if parser.upload:
        if n > 1 and parser.parallel:
            parallelize = True
            if n > np:
                n = np
            pool = mp.Pool(n)
        else:
            parallelize = False
        additional_arguments = []
        for k, v in variables["upload"].items():
            additional_arguments += [f"{k}", f"{v}"]
        if parser.no_upload:
            additional_arguments += ["-nu"]
        arguments = [
            (
                ["-dcl"]
                + base[2:-1]
                + [organism]
                + ["-p", f"{parser.port}", "-ip", f"{parser.ip}"]
                + additional_arguments
            )
            for organism in parser.organism
        ]

        if parallelize:
            pool.map_async(main, arguments)
            pool.close()
            pool.join()
        else:
            for arg in arguments:
                main(arg)


def main(args=None):
    """Main function to construct the node layout and link layout files which can be uploaded to the VRNetzer website. This is to reproduce the full interactome STRING networks from scratch. If benchmark is on it will benchmark the runtime of the different steps."""
    parser = arg_parser.parse_args(args)
    runtimes = {}
    if parser.benchmark:
        total_runtime = timeit.default_timer()

    if "reproduce" in parser.organism:
        reproduce_networks(parser)
    else:
        if "all" in parser.organism:
            parser.organism = Organisms.all_organisms
        runtimes = workflow(parser)

    if parser.benchmark:
        report_runtimes(total_runtime, runtimes)


def report_runtimes(total_runtime, runtimes) -> None:
    total_runtime = timedelta(seconds=timeit.default_timer() - total_runtime)
    st.log.info(f"Overall runtime of Process: \t\t\t\t{total_runtime}")
    st.log.info(f"=" * 50)
    for organism, r in runtimes.items():
        total_runtime = r.pop("total")
        st.log.info(f"Total runtime for {organism}: \t\t\t\t{total_runtime}")
        st.log.info(f"=" * 50)
        for step, runtime in r.items():
            if runtime:
                st.log.info(f"Runtime of step {step}: \t{runtime}")


if __name__ == "__main__":
    main()
