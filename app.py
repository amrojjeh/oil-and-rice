from uuid import uuid4
import json
import os
from flask import Flask, abort, render_template, request, redirect, url_for
from werkzeug.utils import secure_filename

def new_well():
    return {
        "name": "Default well",
        "assets": []
    }

app = Flask(__name__)

def read_wells():
    wells = {}
    for well_filename in os.listdir("wells"):
        with open(f"wells/{well_filename}", "r") as well_file:
            well_route = well_filename.removesuffix(".json")
            wells[well_route] = json.loads(well_file.read())
            wells[well_route]["route"] = well_route
    return wells

@app.route("/")
def index():
    return redirect("/well/default")

@app.route("/well/<name>")
def well(name):
    if not os.path.isfile(f"wells/{name}.json"):
        if name == "default":
            with open("wells/default.json", "w+") as f:
                f.write(json.dumps(new_well()))
        else:
            abort(404)
    wells = read_wells()
    selected = wells[name]
    return render_template("index.html", wells=wells, selected=selected)

@app.route("/well/<name>/add-pdf", methods=["GET", "POST"])
def add_pdf(name):
    if request.method == "GET":
        wells = read_wells()
        selected = wells[name]
        return render_template("add_pdf.html", selected=selected)
    for file in request.files.getlist("file"):
        file_id = uuid4()
        file.save(f"uploads/{secure_filename(str(file_id))}.json")
        # Assume well exists
        data = None
        with open(f"wells/{name}.json", "r") as well_file:
            data = json.loads(well_file.read())
        with open(f"wells/{name}.json", "w") as well_file:
            data["assets"].append({"name": file.filename, "id": str(file_id)})
            well_file.write(json.dumps(data))
    return redirect(url_for("index"))
