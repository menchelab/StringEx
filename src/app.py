import json
import multiprocessing as mp
import os

import flask
import GlobalData as GD
from io_blueprint import IOBlueprint
from project import Project

import util

from . import routes
from . import settings as st
from . import util as string_util
from . import workflows as wf
from .send_to_cytoscape import send_to_cytoscape

url_prefix = "/StringEx"

blueprint = IOBlueprint(
    "StringEx",
    __name__,
    url_prefix=url_prefix,
    template_folder=st._THIS_EXT_TEMPLATE_PATH,
    static_folder=st._THIS_EXT_STATIC_PATH,
)

column_2 = ["string_main_tab.html", "string_send_subset.html"]
upload_tabs = ["string_upload_tab.html", "string_map_tab.html"]

"""Setup function to prepare the STRING Uploader and move the prepared STRING interactomes from the StringEx directory to the projects directory of the VRNetzer backend."""
string_util.pepare_uploader()
string_util.move_on_boot()


@blueprint.before_app_first_request
@blueprint.route("/preview", methods=["GET"])
def string_preview():
    """Route to STRING WEBGL Preview. If No project is selected, redirect to the project selection page of the StringEx WEBGL preview. this function is based on the preview function of base VRNetzer app.py."""
    return routes.preview()


@blueprint.route("/uploadfiles", methods=["GET", "POST"])
def string_ex_upload_files() -> str:
    """This route is used to upload a VRNetz using the STRING Uploader. A POST request is send to it, when a user clicks the "upload" button.

    Returns:
        str: A status giving information whether the upload was successful or not.
    """
    return routes.upload_files()


@blueprint.route("/mapfiles", methods=["GET", "POST"])
def string_ex_map_files():
    """This route is used to map a small VRNetz onto full genome STRING interactomes. A POST request is send to it, when a user clicks the "map" button.
    Returns:
        str: A status giving information whether the upload was successful or not.
    """
    return routes.map_files()


@blueprint.route("/receiveNetwork", methods=["POST"])
def string_ex_receive_network_json():
    """This route accepts a network in the form of a JSON object. The JSON object is then used downstream to create a VRNetzer project out of it. This route is mainly used to send a network to the VRNetzer from Cytoscape."""
    receiveNetwork = flask.request.get_json()
    wf.VRNetzer_send_network_workflow(receiveNetwork, blueprint)
    project = receiveNetwork["form"]["project"]
    return json.dumps({"url": f"/StringEx/resultPage/{project}"})


@blueprint.route("/resultPage/<project>", methods=["GET"])
def string_ex_result_page(project):
    """Is used to present that the sending of a network was successful and provides access to layout changing etc. Used in the to provide Cytoscape user with the result of the network upload process."""
    username = util.generate_username()
    layouts = ""
    flask.session["username"] = username
    flask.session["room"] = 1
    project = Project(project)
    return flask.render_template(
        "string_send_result_page.html",
        project=project.name,
        layouts=layouts,
        pfile=project.pfile,
        pdata=json.dumps(project.pfile),
        # sessionData=json.dumps(GD.sessionData),
    )


@blueprint.route("/")
def string_ex_index():
    """Redirect to the main index page as the StringEx extension does not have a dedicated index page."""
    return flask.redirect("/")


@blueprint.route("/receiveInteractome", methods=["POST"])
def string_ex_receive_interactome():
    """Route to receive the interactome from prepared by a client using the the provided script. Can be used to upload an interactome prepared with the script provided with StringEx. It will update some annotations data and pfile information of the uploaded projects and trigger the annotation scraper if it is existing."""
    data = {"project_name": flask.request.args.get("project_name")}
    files = flask.request.files
    data["host"] = flask.request.host
    res = routes.receive_interactome(data, files)
    if hasattr(GD, "annotationScraper"):
        GD.annotationScraper.update_annotations(data["project_name"])
    return res


@blueprint.route("/status", methods=["GET"])
def string_ex_status():
    """Route to check if the StringEx extension is installed and running."""
    return "StringEx is installed and running..."


@blueprint.on(
    "send_to_cytoscape",
)
def string_send_to_cytoscape(message):
    """Is triggered by a call of a client. Will take the current selected nodes and links to send them to a running instance of Cytoscape. This will always send the network the Cytoscape session of the requesting user, if not otherwise specified. If to host is selected, the network will be send to the Cytoscape session of the Server host."""
    return_dict = mp.Manager().dict()
    ip = flask.request.remote_addr
    user = message.get("user", util.generate_username())
    p = mp.Process(
        target=send_to_cytoscape,
        args=(message, ip, user, return_dict, GD.pfile, GD.sessionData["actPro"]),
    )
    p.start()
    p.join(timeout=300)
    p.terminate()
    if p.exitcode is None:
        return_dict["status"] = {
            "message": f"Process timed out. Please do not remove networks or views fom Cytoscape while the process is running.",
            "status": "error",
        }
    blueprint.emit("status", return_dict["status"])
