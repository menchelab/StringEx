import flask
from . import settings as st
import uploader
import json
import GlobalData as GD
import os
from PIL import Image
from . import workflows as wf
from . import util as string_util
import pandas as pd
from . classes import VRNetzElements as VRNE
def upload_files():
    form = flask.request.form.to_dict()
    vr_netz_files = flask.request.files.getlist("vrnetz")
    if len(vr_netz_files) == 0 or vr_netz_files[0].filename == "":
        st.log.error(f"No VRNetz file provided!")
        return '<a style="color:red;"href="/upload">ERROR invalid VRNetz file!</a>'
    network_file = vr_netz_files[0]
    network = network_file.read().decode("utf-8")
    try:
        network = json.loads(network)
    except json.decoder.JSONDecodeError:
        st.log.error(f"Invalid VRNetz file:{network_file.filename}")
        return '<a style="color:red;">ERROR invalid VRNetz file!</a>'
    project_name = ""
    overwrite_project = False
    if form["string_namespace"] == "New":
        project_name = form["string_new_namespace_name"]
        overwrite_project = True
    else:
        project_name = form["existing_namespace"]
    algo = form.get("string_algo")
    tags = {
        "stringify": False,
        "string_write": False,
        "string_calc_lay": False,
    }
    for key, _ in tags.items():
        if key in form:
            tags[key] = True
    algo_variables = string_util.get_algo_variables(algo, form)
    layout_name = form.get("string_layout_name", "3d")
    if layout_name == "":
        layout_name = "3d"
    return wf.VRNetzer_upload_workflow(
        network,
        network_file.filename,
        project_name,
        algo,
        tags,
        algo_variables,
        layout_name,
        overwrite_project=overwrite_project,
    )


def map_files():
    form = flask.request.form.to_dict()
    f_src_network = flask.request.files.getlist("vrnetz")
    vr_netz_files = flask.request.files.getlist("vrnetz")
    if len(vr_netz_files) == 0:
        return flask.redirect("/upload")
    f_src_network = vr_netz_files[0]
    src_network = f_src_network.read().decode("utf-8")
    try:
        src_network = json.loads(src_network)
    except json.decoder.JSONDecodeError:
        st.log.error(f"Invalid VRNetz file:{f_src_network}")
        return '<a style="color:red;">ERROR invalid VRNetz file!</a>'
    
    # src_network[VRNE.nodes] = pd.DataFrame(src_network[VRNE.nodes])
    # src_network[VRNE.links] = pd.DataFrame(src_network[VRNE.links])

    organism = form.get("string_organism")
    project_name = form.get("string_map_project_name")
    src_filename = f_src_network.filename
    return wf.VRNetzer_map_workflow(src_network, src_filename, organism, project_name)


def preview():
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
    for x in range(length):
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
