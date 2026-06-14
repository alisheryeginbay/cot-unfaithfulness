#!/usr/bin/env bash
# Compile the TikZ schematic to PDF and convert to PNG + SVG in results/figures/.
# Run from the repo root: bash scripts/build_schematic.sh
set -euo pipefail

export PATH="/Library/TeX/texbin:$PATH"
export SOURCE_DATE_EPOCH=0  # deterministic PDF timestamps

repo_root="$(cd "$(dirname "$0")/.." && pwd)"
cd "$repo_root"

out_dir="results/figures"
stem="hint_schematic"
tmp_dir="$(mktemp -d)"
trap 'rm -rf "$tmp_dir"' EXIT

# Refresh palette colours from palette.toml (the single colour source).
uv run python scripts/gen_palette_tex.py

# pdflatex needs palette.tex on its input path; compile from scripts/ into a temp dir.
( cd scripts && pdflatex -interaction=nonstopmode -halt-on-error \
    -output-directory "$tmp_dir" "$stem.tex" >/dev/null )

mkdir -p "$out_dir"
cp "$tmp_dir/$stem.pdf" "$out_dir/$stem.pdf"
pdftocairo -png -r 300 -singlefile "$out_dir/$stem.pdf" "$out_dir/$stem"
pdftocairo -svg "$out_dir/$stem.pdf" "$out_dir/$stem.svg"

echo "wrote $out_dir/$stem.{pdf,png,svg}"
