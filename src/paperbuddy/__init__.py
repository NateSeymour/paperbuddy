import pathlib
import json
import argparse
import json2latex
import os
import pypandoc
import subprocess
import shutil
import watchdog.events
import watchdog.observers
import time
import re

def resolve_project(path):
    path = pathlib.Path(path)

    project = {}

    if not path.exists():
        print(f"[ERROR] {path} does not exist.")
        exit(1)

    if path.is_dir():
        with open(f"{path}/paper.json") as file:
            project = json.load(file)

    available_templates = {}
    template_directories = [path]

    for dir in template_directories:
        for child in dir.iterdir():
            if child.suffix == ".tex":
                available_templates[child.stem] = child.resolve()

    return project, available_templates

# Initializes a directory for a new paper project
def init(args):
    options = {
        "version": 1,
        "template": "simple",
        "title": "-",
        "author": "-",

        "build": {
            "plugins": [],
        },
    }

    pathlib.Path(args.path).mkdir(exist_ok=True)
    pathlib.Path(f"{args.path}/build").mkdir(exist_ok=True)
    pathlib.Path(f"{args.path}/content").mkdir(exist_ok=True)
    pathlib.Path(f"{args.path}/content/main.md").write_text("# Welcome to my Paper")
    pathlib.Path(f"{args.path}/paper.json").write_text(json.dumps(options))
    pathlib.Path(f"{args.path}/sources.bib").write_text("\n")
    pathlib.Path(f"{args.path}/.gitignore").write_text("build")

# Builds project
def build(args):
    project, available_templates = resolve_project(args.path)

    # Generate temporary build files
    pathlib.Path("build").mkdir(exist_ok=True)

    # Abbreviations
    if "abbreviations" in paper:
        abbreviations = ""

        abbreviations += "\\begin{acronym}\n"

        for abbreviation, value in paper["abbreviations"].items():
            abbreviations += f"\t\\acro{{{abbreviation}}}{{{value}}}\n"

        abbreviations += "\\end{acronym}\n"

        with open("build/abbreviations.tex", "w") as file:
            file.write(abbreviations)

    # Content
    sources = [f for f in pathlib.Path("content").rglob("*.md")]
    for source in sources:
        raw = source.read_text(encoding="utf-8")

        # Process quotes
        raw = re.sub(r'"([^"]*)"', r"\\enquote{\1}", raw)

        # Process commands
        raw = re.sub(r'#([a-zA-Z]+)/([a-zA-Z\-]+)', r"\\\1{\2}", raw)

        # Write output
        pypandoc.convert_text(raw, format="markdown+mark", to="latex", outputfile=f"build/{source.stem}.tex")

    # Data
    with open("build/__data.tex", "w") as file:
        file.write(json2latex.dumps("data", paper))

    # Run tool
    if shutil.which("latexmk"):
        subprocess.run([
            "latexmk",
            "-pdf",
            "-quiet",
            "-outdir=build",
            template_path.resolve()
        ])
    else:
        print("Error: could not locate latexmk!")
        exit(1)

    print("Build complete!")

# Process arguments
parser = argparse.ArgumentParser(description="Generates Academic Paper from Course Files")
subparsers = parser.add_subparsers(dest="command", required=True)

parser_init = subparsers.add_parser("init")
parser_init.add_argument("path", default=".")
parser_init.add_argument("--simple", action="store_true")
parser_init.set_defaults(func=init)

parser_build = subparsers.add_parser("build")
parser_build.add_argument("path", default=".")
parser_build.add_argument("--watch", action="store_true")
parser_build.set_defaults(func=build)

args = parser.parse_args()
args.func(args)

# Grab template directory
templates = pathlib.Path("templates").resolve()

# CWD
os.chdir(pathlib.Path(args.source).resolve())

# Read paper information
paper = {}
with open("paper.json") as file:
    paper = json.load(file)

print(f"Building paper...")

# Get template
template_path = pathlib.Path(f"{templates.resolve()}/{paper["meta"]["template"]}.tex")
print(f"Using template in {template_path.resolve()}")

build()

class FileChangeEventHandler(watchdog.events.FileSystemEventHandler):
    def on_any_event(self, event: watchdog.events.FileSystemEvent):
        print("Change detected. Rebuilding...")
        build()

if args.watch:
    print("Watching for file changes...")

    observer = watchdog.observers.Observer()
    observer.schedule(FileChangeEventHandler(), "content", recursive=True)
    observer.start()

    try:
        while True:
            time.sleep(1)
    finally:
        observer.stop()
        observer.join()
