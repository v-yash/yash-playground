from flask import Flask, render_template, request, send_file
import os

app = Flask(__name__)
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../"))

@app.route("/")
def index():
    return browse_directory(BASE_DIR)

@app.route("/browse/")
@app.route("/browse/<path:subpath>")
def browse_directory(subpath=""):
    full_path = os.path.join(BASE_DIR, subpath)

    if os.path.isfile(full_path):  # Show file contents
        return send_file(full_path)
    
    items = sorted(os.listdir(full_path))
    return render_template("index.html", path=subpath, items=items)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
