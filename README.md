# paperbuddy

`paperbuddy` is a simple tool that processes markdown files into latex and automatically compiles them into PDF files with `latexmk`.

## Features

- Custom latex commands with `#tag` syntax. `#parencite/seymour-2026` expands to `\parencite{seymour-2026}`.
- Custom templates supported.
- Automatic detection and wrapping of quotes in `\enquote` for localized quotation marks.
- Automatic creation of table of abbreviations based on configuration file.
- Automatic recompilation on change of source files with `paperbuddy watch`.

## Usage

- `paperbuddy init [path]` - Initializes a new project and creates source tree.
- `paperbuddy build [path]` - Build paper.
- `paperbuddy watch [path]` - Watches source directory and rebuilds on files changes.