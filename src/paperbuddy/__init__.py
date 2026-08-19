import pathlib
import json
import argparse
import json2latex
import pypandoc
import subprocess
import shutil
import watchdog.events
import watchdog.observers
import time
import re
import os
import sys
import importlib.resources

class FileChangeEventHandler(watchdog.events.FileSystemEventHandler):
    def on_any_event(self, event: watchdog.events.FileSystemEvent):
        print("Change detected. Rebuilding...")
        build(**self.build_args)

    def __init__(self, **kwargs):
        self.build_args = kwargs

def create_files(files, base=".", allow_exists=True):
    pathlib.Path(base).mkdir(allow_exists)

    for path, content in files:
        file = pathlib.Path(f"{base}/{path}")

        if content == None:
            file.mkdir(allow_exists)
        else:
            file.write_text(content)

def resolve_paper(path):
    path = pathlib.Path(path)

    if not path.exists():
        print(f"[ERROR] {path} does not exist.")
        exit(1)

    if path.is_dir():
        with open(f"{path}/paper.json") as file:
            return json.load(file)
    else:
        print(f"[ERROR] {path} does not contain a valid project.")
        exit(1)

# Initializes a directory for a new paper project
def init(path, title="My Paper", template="simple", author="Me", **kwargs):
    print(f"Creating new project in {path}...")

    if pathlib.Path(path).exists():
        print(f"[ERROR] project already exists in `{path}`.")
        exit(1)

    create_files(base=path, files=[
        ("build", None),
        ("content", None),
        ("content/main.md", f"# {title}"),
        ("templates", None),
        ("paper.json", json.dumps({
            "version": 1,
            "template": template,
            "title": title,
            "author": author,

            "build": {
                "plugins": [],
            },
        }, indent=4)),
        ("sources.bib", "\n"),
        (".gitignore", "build"),
    ])

# Builds project
def build(path, **kwargs):
    os.chdir(pathlib.Path(path).resolve())

    paper = resolve_paper(".")

    # Resolve all possible templates
    available_templates = {}
    template_directories = [
        pathlib.Path("./templates")
    ]

    # Add built-in templates
    builtin_template_directory = importlib.resources.files("paperbuddy").joinpath("templates")
    with importlib.resources.as_file(builtin_template_directory) as local_path:
        template_directories.insert(0, local_path.absolute())

    # Process template directories
    for template_directory in template_directories:
        if not template_directory.exists():
            continue

        for child in template_directory.iterdir():
            if child.suffix == ".tex":
                available_templates[child.stem] = child.resolve()

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

    # Resolve template
    template = paper.get("template", "simple")

    if template not in available_templates:
        print(f"[ERROR] template `{template}` could not be found.")
        exit(1)

    template_path = available_templates[template]

    # Run tool
    if shutil.which("latexmk"):
        subprocess.run([
            "latexmk",
            "-pdf",
            "-quiet",
            "-outdir=build",
            template_path
        ])
    else:
        print("Error: could not locate latexmk!")
        exit(1)

    print("Build complete!")


def watch(**kwargs):
    print("Watching sources...")

    observer = watchdog.observers.Observer()
    observer.schedule(FileChangeEventHandler(**kwargs), "content", recursive=True)
    observer.start()

    build(**kwargs)

    try:
        while True:
            time.sleep(1)
    finally:
        observer.stop()
        observer.join()

def info(**kwargs):
    print("paperbuddy v0.3.0 by Nathan Seymour <nathan@seymour.global>")
    print(f"Installed in `{sys.prefix}`")

def main():
    # Process arguments
    parser = argparse.ArgumentParser(description="Generates Academic Paper from Course Files")
    subparsers = parser.add_subparsers(dest="command", required=True)

    parser_init = subparsers.add_parser("init")
    parser_init.add_argument("path", nargs="?", default=".")
    parser_init.set_defaults(func=init)

    parser_build = subparsers.add_parser("build")
    parser_build.add_argument("path", nargs="?", default=".")
    parser_build.set_defaults(func=build)

    parser_watch = subparsers.add_parser("watch")
    parser_watch.add_argument("path", nargs="?", default=".")
    parser_watch.set_defaults(func=watch)

    parser_info = subparsers.add_parser("info")
    parser_info.set_defaults(func=info)

    args = parser.parse_args()
    args.func(**vars(args))
