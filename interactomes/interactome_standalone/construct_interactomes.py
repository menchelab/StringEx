#!Python3
import argparse
import os
import timeit
from logging.handlers import RotatingFileHandler

import src.load_files as load_files
import src.logger as log
import src.read_string as read_string
from src.classes import LayoutAlgroithms, Organisms

f_handler = RotatingFileHandler(
    os.path.join("logs", "interactome_construction.log"),
    mode="a",
    maxBytes=5 * 1024 * 1024,
    backupCount=2,
    encoding=None,
    delay=0,
)
f_handler.setLevel(log._LOG_LEVEL)
f_handler.setFormatter(log._LOG_FORMAT)
log.log.addHandler(f_handler)
_SOURCE_FILES = os.path.join(".","string_interactomes")
_OUTPUT_PATH = os.path.join(".","csv","string_interactomes")

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
        log.log.info(f"Processing organism: {organism} with taxonomy id: {tax_id}.")
        start = timeit.default_timer()
        end_download,end_construct,end_layout,end_upload = None, None, None, None
        if parser.download:
            start_download = timeit.default_timer()
            load_files.download(tax_id, organism, parser.src_dir,clean_name)
            end_download = round((timeit.default_timer()-start_download)*10**6,3)
            log.log.debug(f"Runtime of download: {end_download/1000} ms")

        if parser.construct:
            start_construct = timeit.default_timer()
            read_string.construct_graph(parser.src_dir, organism,clean_name)
            end_construct = round((timeit.default_timer()-start_construct)*10**6,3)
            log.log.debug(f"Runtime of construct: {end_construct/1000} ms")

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
            start_layout = timeit.default_timer()
            read_string.construct_layouts(clean_name, parser.src_dir, parser.layout_algo, variables)
            end_layout = round((timeit.default_timer()-start_layout)*10**6,3)
            log.log.debug(f"Runtime of layout_calc: {end_layout/1000} ms")

        ###### Irrelevant for runtime, can ignore
        # if parser.upload:
        #     start_upload = timeit.default_timer()
        #     upload_network.upload(clean_name, parser.tarball, parser.output_dir, parser.ip, parser.port)
        #     end_upload = round((timeit.default_timer()-start_upload)*10**6,3)
        #     log.log.debug(f"Runtime of upload: {end_upload/1000} ms")

        end = round((timeit.default_timer()-start)*10**6,3)
        log.log.debug(f"Overall runtime:{end} ms")
        log.log.debug("====================")
        for flag,name,runtime in zip([parser.download,parser.construct,parser.layout,parser.upload],["Download","Construct","Layout","Upload"],[end_download,end_construct,end_layout,end_upload]):
            if flag:
                if runtime is not None:
                    log.log.debug(f"{name}\t{runtime/1000} ms")
                    
if __name__ == "__main__":
    parser = parse_args()
    main(parser)