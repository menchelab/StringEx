import json
import os
import random

import flask
from PIL import Image

import GlobalData as GD
import uploader

from . import settings as st
from . import workflows as wf

url_prefix = "/StringEx"

blueprint = flask.Blueprint(
    "StringEx",
    __name__,
    url_prefix=url_prefix,
    template_folder=st._FLASK_TEMPLATE_PATH,
    static_folder=st._FLASK_STATIC_PATH,
)


@blueprint.route("/main")
def string_main():
    """Route to STRING Main panel"""
    username = flask.request.args.get("usr")
    if username is None:
        username = str(random.randint(1001, 9998))
    else:
        username = username + str(random.randint(1001, 9998))
        print(username)
    project = flask.request.args.get("project")

    if project is None or project == "none":
        project = uploader.listProjects()[0]
    print(project)
    if flask.request.method == "GET":

        room = 1
        # Store the data in session
        flask.session["username"] = username
        flask.session["room"] = room
        # prolist = listProjects()
        folder = "static/projects/" + project + "/"

        # Update global pfile and global names variables
        with open(folder + "pfile.json", "r") as json_file:
            GD.pfile = json.load(json_file)

        with open(folder + "names.json", "r") as json_file:
            GD.names = json.load(json_file)

        return flask.render_template(
            # "/mainpanel/string_main.html",
            "/string_main.html",
            session=flask.session,
            sessionData=json.dumps(GD.sessionData),
            pfile=json.dumps(GD.pfile),
        )
    else:
        return "error"


@blueprint.route("/preview", methods=["GET"])
def string_preview():
    """Route to STRING WEBGL Preview. If No project is selected, redirect to the project selection page of the StringEx WEBGL preview. this function is based on the preview function of base VRNetzer app.py."""
    data = {}

    if flask.request.args.get("project") is None:

        print("project Argument not provided - redirecting to menu page")

        data["projects"] = uploader.listProjects()
        print(data["projects"])
        return flask.render_template("threeJS_VIEWER_Menu.html", data=json.dumps(data))

    layoutindex = flask.request.args.get("layout")
    if layoutindex is None:
        layoutindex = 0
    else:
        layoutindex = int(layoutindex)

    layoutRGBIndex = flask.request.args.get("ncol")
    if layoutRGBIndex is None:
        layoutRGBIndex = 0
    else:
        layoutRGBIndex = int(layoutRGBIndex)

    linkRGBIndex = flask.request.args.get("lcol")
    if linkRGBIndex is None:
        linkRGBIndex = 0
    else:
        linkRGBIndex = int(linkRGBIndex)

    project = flask.request.args.get("project")
    GD.sessionData["actPro"] = project

    y = '{"nodes": [], "links":[]}'
    testNetwork = json.loads(y)

    pname = os.path.join(st._PROJECTS_PATH, project, "pfile")
    p = open(pname + ".json", "r")
    thispfile = json.load(p)
    thispfile["selected"] = [layoutindex, layoutRGBIndex, linkRGBIndex]

    name = os.path.join(st._PROJECTS_PATH, project, "nodes")
    n = open(name + ".json", "r")
    nodes = json.load(n)
    nlength = len(nodes["nodes"])

    lname = os.path.join(st._PROJECTS_PATH, project, "links")
    f = open(lname + ".json", "r")
    links = json.load(f)
    length = len(links["links"])

    nodes_im = os.path.join(
        st._PROJECTS_PATH,
        project,
        "layouts",
        thispfile["layouts"][layoutindex] + ".bmp",
    )
    im = Image.open(nodes_im, "r")

    nodes_iml = os.path.join(
        st._PROJECTS_PATH,
        project,
        "layoutsl",
        thispfile["layouts"][layoutindex] + "l.bmp",
    )
    iml = Image.open(nodes_iml, "r")

    nodes_col = os.path.join(
        st._PROJECTS_PATH,
        project,
        "layoutsRGB",
        thispfile["layoutsRGB"][layoutRGBIndex] + ".png",
    )
    imc = Image.open(nodes_col, "r")

    links_col = os.path.join(
        st._PROJECTS_PATH,
        project,
        "linksRGB",
        thispfile["linksRGB"][linkRGBIndex] + ".png",
    )
    imlc = Image.open(links_col, "r")

    pixel_values = list(im.getdata())
    pixel_valuesl = list(iml.getdata())
    pixel_valuesc = list(imc.getdata())
    pixel_valueslc = list(imlc.getdata())

    for i, x in enumerate(pixel_values):
        if i < nlength:
            newnode = {}
            pos = [
                float(x[0] * 255 + pixel_valuesl[i][0]) / 65536 - 0.5,
                float(x[1] * 255 + pixel_valuesl[i][1]) / 65536 - 0.5,
                float(x[2] * 255 + pixel_valuesl[i][2]) / 65536 - 0.5,
            ]

            newnode["p"] = pos
            newnode["c"] = pixel_valuesc[i]
            newnode["n"] = nodes["nodes"][i]["n"]
            testNetwork["nodes"].append(newnode)

    if length > 30000:
        length = 30000
    for x in range(length - 1):
        newLink = {}
        newLink["id"] = x
        newLink["s"] = links["links"][x]["s"]
        newLink["e"] = links["links"][x]["e"]
        newLink["c"] = pixel_valueslc[x]
        testNetwork["links"].append(newLink)

    return flask.render_template(
        "string_preview.html",
        data=json.dumps(testNetwork),
        pfile=json.dumps(thispfile),
        sessionData=json.dumps(GD.sessionData),
    )


@blueprint.route("/upload", methods=["GET"])
def string_upload():
    """Rout to upload a new .VRNetz file to create a new project. This function is based on the upload function of base VRNetzer app.py."""
    GD.sessionData["layoutAlgos"] = st.LayoutAlgroithms.all_algos
    GD.sessionData["actAlgo"] = st.LayoutAlgroithms.spring
    GD.sessionData["organisms"] = st.Organisms.all_organisms
    """Route to STRING upload."""
    prolist = uploader.listProjects()
    html_page = "string_upload.html"
    return flask.render_template(
        html_page,
        namespaces=prolist,
        algorithms=GD.sessionData["layoutAlgos"],
        organisms=GD.sessionData["organisms"],
    )


@blueprint.route("/uploadfiles", methods=["GET", "POST"])
def string_ex_upload():
    """Route to execute the upload of a VRNetz using the STRING Uploader."""
    return wf.VRNetzer_upload_workflow(flask.request)


@blueprint.route("/mapfiles", methods=["GET", "POST"])
def string_ex_map():
    """Route to Map a small String network to a genome scale network."""
    return wf.VRNetzer_map_workflow(flask.request)


def prepare_session_data():
    """This will setup the username in the flask.session."""
    username = flask.request.args.get("usr")
    if username is None:
        username = str(random.randint(1001, 9998))
    else:
        username = username + str(random.randint(1001, 9998))
    flask.session["username"] = username
