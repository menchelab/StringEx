from interactomes import data_io
from interactomes import functional_annotations as fa
from src.classes import NodeTags as NT
import os
import matplotlib.pyplot as plt
import pandas as pd
import timeit
from datetime import timedelta
from interactomes import data_io


def plot_feature_distribution(_dir: str, organism: str, threshold: float = 0.0):
    """Plot the distribution of feature counts for each feature matrix."""
    feature_matrices = {}
    for fm in os.listdir(os.path.join(_dir, organism, "functional_annotations", "fm")):
        if fm.endswith(".pickle"):
            category = fm.strip(".pickle")
            feature_matrices[category] = pd.read_pickle(
                os.path.join(_dir, organism, "functional_annotations", "fm", fm)
            )
            feature_matrices[category]["annotations"].hist(
                bins=max(feature_matrices[category]["annotations"])
            )
            plt.title(category)
            plt.show()


def main(parser, clean_name):
    fm_runtimes = None

    def construct_fm():
        fa.construct_feature_matrices(
            parser.src_dir,
            clean_name,
            parser.functional_threshold,
        )

    def plot_fm():
        plot_feature_distribution(
            parser.src_dir,
            clean_name,
            parser.functional_threshold,
        )

    if parser.feature_matrices:
        if parser.benchmark:
            construct_runtime = timeit.repeat(
                construct_fm,
                repeat=parser.benchmark_repeat,
                number=parser.benchmark_number,
            )
            average = sum(construct_runtime) / len(construct_runtime)
            construct_runtime = str(timedelta(seconds=average))
            if fm_runtimes is None:
                fm_runtimes = {}
            fm_runtimes["construct_fm"] = construct_runtime
        else:
            construct_fm()

    if parser.plot_feature_matrices:
        if parser.benchmark:
            plot_runtime = timeit.repeat(
                plot_fm,
                repeat=parser.benchmark_repeat,
                number=parser.benchmark_number,
            )
            average = sum(plot_runtime) / len(plot_runtime)
            plot_runtime = str(timedelta(seconds=average))
            if fm_runtimes is None:
                fm_runtimes = {}
            fm_runtimes["plot_fm"] = plot_runtime
        else:
            plot_fm()

    return fm_runtimes
