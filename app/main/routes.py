from pathlib import Path

from flask import Blueprint, current_app, render_template, send_from_directory

main_bp = Blueprint("main", __name__)


@main_bp.route("/")
def index():
    # The built React site is the website. The HTML template remains for tests when it is not built.
    react_index = Path(current_app.root_path).parent / "frontend" / "dist" / "index.html"
    if react_index.is_file():
        return send_from_directory(react_index.parent, "index.html")
    return render_template("index.html")
