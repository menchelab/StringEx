#!Python3
import argparse
import logging
import os
import sys
from logging.handlers import RotatingFileHandler

import interactomes.load_files as load_files
import interactomes.read_string as read_string
import interactomes.upload_network as upload_network
from src import settings as st
from src import util
from src.classes import LayoutAlgroithms, Organisms

f_handler = RotatingFileHandler(
    os.path.join("logs", "interactome_construction.log"),
    mode="a",
    maxBytes=5 * 1024 * 1024,
    backupCount=2,
    encoding=None,
    delay=0,
)
f_handler.setLevel(st._LOG_LEVEL)
f_handler.setFormatter(st._LOG_FORMAT)
st.log.addHandler(f_handler)
_SOURCE_FILES = os.path.join(st._THIS_EXT_STATIC_PATH,"string_interactomes")
_OUTPUT_PATH = os.path.join(st._STATIC_PATH,"csv","string_interactomes")

def parse_args():
    parser = argparse.ArgumentParser(description="Construct STRING interactomes")
    parser.add_argument("organism",type=str,help="Organism to construct the interactome for.",choices=Organisms.all_organisms,nargs="*")
    parser.add_argument("--download","-d",action="store_false",help="Download the interactome files from the STRING website.")
    parser.add_argument("--construct","-c",action="store_false",help="Construct the interactome files from the downloaded files.")
    parser.add_argument("--layout","-l",action="store_false",help="Construct the node and link layout files from the interactome files.")
    parser.add_argument("--upload","-u",action="store_false",help="Upload the node and link layout files to the VRNetzer website.")
    parser.add_argument("-ip",type=str,help="IP address of the VRNetzer website.",default="localhost")
    parser.add_argument("--port","-p",type=int,help="Port of the VRNetzer website.",default=5000)
    parser.add_argument("--tarball","-tar",type=str,help="Path to the directory where the tarball can be found.",default=_SOURCE_FILES)
    parser.add_argument("-output_dir","-out",type=str,help="Path to the output directory where the interactome files should be stored.",default=_OUTPUT_PATH)
    parser.add_argument("--src_dir","-src",type=str,help="Path to the directory where the interactome files are stored.",default=_SOURCE_FILES)
    parser.add_argument("--layout_algo","-lay",type=str,help="Defines the layout algorithm which should be used.",default=LayoutAlgroithms.spring,choices=LayoutAlgroithms.all_algos)
    # TODO: Ask christ about the parameters
    parser.add_argument("--prplxty","-prp",type=int,help="Prplxty parameter of cartoGRAPHs local algorithms.",default=50)
    parser.add_argument("--density","-den",type=int,help="Density parameter of cartoGRAPHs local algorithms.",default=12)
    parser.add_argument("--lrate","-lra",type=int,help="l_rate parameter of cartoGRAPHs local algorithms.",default=200)
    parser.add_argument("--steps","-st",type=int,help="Step parameter of cartoGRAPHs local algorithms.",default=250)
    parser.add_argument("--n_neighbors","-nn",type=int,help="Defines the number of neighbor parameter of cartoGRAPHs global algorithms.",default=10)
    parser.add_argument("--spread","-spr",type=float,help="Defines the spread parameter of cartoGRAPHs global algorithms.",default=1.0)
    parser.add_argument("--min_dist","-md",type=float,help="Defines the min_dist parameter of cartoGRAPHs global algorithms.",default=0.1)
    parser.add_argument("--opt_dist","-opd",type=int,help="Defines the optimal distance parameter k of NetworkX's spring algorithm.",default=250)
    parser.add_argument("--iterations","-it",type=int,help="Defines the number of iterations parameter of NetworkX's spring algorithm.",default=50)
    parser.add_argument("--spring_threshold","-spth",type=int,help="Defines the threshold parpameter of NetworkX's spring algorithm.",default=15)
    return parser.parse_args()
    
def main(parser:dict):
    """Main function to construct the node layout and link layout files which can be uploaded to the VRNetzer website. This is to reproduce the full interactome STRING networks from scratch."""
    for organism in parser.organism:
        tax_id = Organisms.get_tax_ids(organism)
        clean_name = Organisms.get_file_name(organism)
        st.log.info(f"Processing organism: {organism} with taxonomy id: {tax_id}.")
        if parser.download:
            load_files.download(tax_id, organism, parser.src_dir,clean_name)

        if parser.construct:
            read_string.construct_graph(parser.src_dir, organism,clean_name)

        if parser.layout:
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
            read_string.construct_layouts(clean_name, parser.src_dir, parser.layout_algo, variables)

        if parser.upload:
            upload_network.upload(clean_name, parser.tarball, parser.output_dir, parser.ip, parser.port)


if __name__ == "__main__":
    parser = parse_args()
    main(parser)