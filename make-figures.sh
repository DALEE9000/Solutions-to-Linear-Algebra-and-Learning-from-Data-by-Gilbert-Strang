#!/usr/bin/env bash
# Pre-convert the EPS figures to the PDF names graphicx expects.
#
# Why this is needed: pdftex.def converts EPS on the fly by shelling out to
# epstopdf, but the documents live one level below the images, so the conversion
# has to be written to "../chapN/...". Under restricted \write18 -- the default
# -- writing outside the current directory is refused, so the conversion fails
# and the figures come out as draft boxes. Running epstopdf ourselves has no
# such restriction.
#
# The generated PDFs are build artifacts and are gitignored; the .eps files are
# the things under version control. Re-run this after adding or changing a
# figure. Safe to run repeatedly -- it only reconverts what is out of date.

set -euo pipefail
cd "$(dirname "$0")"

converted=0
skipped=0

while IFS= read -r -d '' eps; do
    out="${eps%.eps}-eps-converted-to.pdf"
    if [[ -f "$out" && "$out" -nt "$eps" ]]; then
        skipped=$((skipped + 1))
        continue
    fi
    epstopdf "$eps" --outfile="$out"
    converted=$((converted + 1))
done < <(find . -name '*.eps' -not -path './*/build/*' -print0)

echo "figures: ${converted} converted, ${skipped} already up to date"
