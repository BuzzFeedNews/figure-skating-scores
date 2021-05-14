import pdfplumber
import re
import glob
import sys
import os
from .parsers.common import EmptyResultsException
from .parsers.standard import parse_page as parse_standard
from .parsers.alternative import parse_page as parse_alternative

def parse_page(page):
    """
    This function takes a page object, checks whether there
    are any score sheets on the page, and the parsed out the 
    structured score data from each score sheet
    """

    try:
        text = page.extract_text()

    # If pdfplumber cannot read the page, we note it in the parsing log.
    except Exception:
        sys.stderr.write("*** CANNOT READ ***")
        return None

    # For some pages -- often the graphical cover pages -- pdfplumber
    # can't find any text. We skip over those, and note them in
    # the parsing log.
    if text is None or len(text) == 0:
        sys.stderr.write("*** CANNOT FIND ANY TEXT ***")
        return None

    # All the score sheets should have "JUDGES DETAILS PER SKATER"
    # on the page. If a page doesn't, we continue to the next page.
    if "JUDGES DETAILS PER SKATER" not in text:
        sys.stderr.write("-")
        return None

    # The protocol PDFs we parse use two, slightly different layouts
    # for the score sheets. The code block below detects which to use,
    # and then applies it. See the parsers/ directory for the particular
    # parsing code.
    if "Deductions:" in text:
        parser = parse_alternative
    else:
        parser = parse_standard

    try:
        parsed = parser(page)

    # A few pages of the protocol PDFs have headers that make it
    # look like they'd contain score sheets, but don't. You can
    # check the parsing log to see which these are.
    except EmptyResultsException:
        sys.stderr.write("*** CAN'T FIND PERFORMANCES ON PAGE ***")
        return None

    # If we got this far, we've been able to locate, and parse the
    # score sheets on this page.
    sys.stderr.write("+")

    # Here, we extract the competition and program names,
    # and add them to the parsed data.
    competition, program = text.split("\n")[:2]
    program = re.sub(r"\s+JUDGES DETAILS PER SKATER", "", program).strip()

    for result in parsed:
        result["metadata"]["competition"] = competition
        result["metadata"]["program"] = program

    return parsed

def parse_pdf(pdf):
    """
    This function takes a PDF object, iterates through
    each page, and returns structured data representing for 
    each score sheet it has found.
    """
    performances = []
    for i, page in enumerate(pdf.pages):
        sys.stderr.flush()
        sys.stderr.write("\nPage {:03d}: ".format(i + 1))
        parsed = parse_page(page)
        if parsed is None: continue
        performances += parsed

    sys.stderr.write("\n")
    return performances

def parse_pdf_from_path(path):
    try:
        with pdfplumber.open(path) as pdf:
            return {
                "performances": parse_pdf(pdf),
                "pdf": path.rsplit("/", 1)[-1]
            }

    except pdfplumber.pdfminer.pdfparser.PDFSyntaxError as e:
            sys.stderr.write("*** IS REAL PDF?: {}\n".format(path))

if __name__ == "__main__":
    import json
    for arg in sys.argv[1:]:
        if arg[-4:].lower() == ".pdf":
            paths = [ arg ]
        else:
            paths = sorted(glob.glob(os.path.join(arg, "*.pdf")))

        for i, path in enumerate(paths):
            fname = path.rsplit("/", 1)[-1]
            sys.stderr.write("\n--- {} ---\n".format(fname))
            parsed = parse_pdf_from_path(path)
            dest = os.path.join("data/json", fname[:-4] + ".json")
            with open(dest, "w") as f:
                json.dump(parsed, f, sort_keys=True, indent=2)
