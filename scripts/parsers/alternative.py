import pdfplumber
import pandas as pd
import numpy as np
from .common import EmptyResultsException, dictify


def find_rects(page):
    rects = []
    words = page.extract_words()
    for mark_start, mark_end in [
        ("=", "#"),
        ("Elements", "Factor"),
        ("Factor", "Deductions:")
    ]:
        tops = [ w["bottom"] + 1 for w in words if w["text"] == mark_start ]
        bottoms = [ w["top"] for w in words if w["text"] == mark_end ]
        assert len(tops) == len(bottoms)
        assert len(tops) > 0
        rects += [ {
            "x0": 0,
            "x1": page.width,
            "top": top,
            "bottom": bottom
        } for top, bottom in zip(tops, bottoms) ]
        
    return list(sorted(rects, key=lambda x: x["top"]))

def parse_upper_rect(page, rect):
    h_lines = [ rect["top"], rect["bottom"] ]
    v_lines = [ 45, 80, 240, 270, 310, 380, 420, 500, 550 ]

    rows = page.extract_table({
        "vertical_edges": v_lines,
        "horizontal_edges": h_lines
    })
    assert len(rows) == 1
    return pd.Series(dict(zip([
        "rank",
        "name",
        "nation",
        "starting_number",
        "total_segment_score",
        "total_element_score",
        "total_component_score",
        "total_deductions"
    ], rows[0])))

def parse_elements(page, rect):
    cropped = page.crop(pdfplumber.utils.object_to_bbox(rect))
    tops =  [ x[0]["top"] for x in pdfplumber.utils.cluster_objects(cropped.chars, "top", 0) ]
    h_lines = tops + [tops[-1] + 20]
    
    v_lines = [ 45, 60, 160, 176, 196, 204, 230, ] + \
        [ 271 + x * 20 for x in range(9) ] + \
        [ 510, 550 ]    

    rows = page.extract_table({
        "vertical_edges": v_lines,
        "horizontal_edges": h_lines
    })
    
    df = pd.DataFrame(rows, columns=[
        "element_num",
        "element_desc",
        "info_flag",
        "base_value",
        "credit_flag",
        "goe",
        "J1",
        "J2",
        "J3",
        "J4",
        "J5",
        "J6",
        "J7",
        "J8",
        "J9",
        "ref",
        "scores_of_panel"
    ])\
        .replace("-", np.nan)\
        .replace("", np.nan)

    if (len(df) == 2) and df["base_value"].astype(float).sum() == 0:
        return None
    
    assert df["base_value"].astype(float).pipe(lambda x: x.iloc[-1] / x.sum()).round(3) == 0.5
    assert df["scores_of_panel"].astype(float).pipe(lambda x: x.iloc[-1] / x.sum()).round(3) == 0.5
    
    df = df.iloc[:-1].copy()
    # Removed because sometimes (or at least once), a number is actually missing:
    # assert df["element_num"].astype(int).tolist() == list(range(1, len(df) + 1))

    for i in range(9):
        colname = "J{}".format(i + 1)
        df[colname] = df[colname].astype(float)
    
    for colname in [ "base_value", "goe", "scores_of_panel" ]:
        df[colname] = df[colname].astype(float)
        
    df["element_num"] = df["element_num"].astype(int)
    
    return df

def parse_program_components(page, rect):
    cropped = page.crop(pdfplumber.utils.object_to_bbox(rect))
    tops =  [ x[0]["top"] for x in pdfplumber.utils.cluster_objects(cropped.chars, "top", 0) ]
    h_lines = tops + [ rect["bottom"] ]
    
    v_lines = [ 45, 204, 230, ] + \
        [ 271 + x * 20 for x in range(9) ] + \
        [ 510, 550 ]


    rows = page.extract_table({
        "vertical_edges": v_lines,
        "horizontal_edges": h_lines
    })
    
    df = pd.DataFrame(rows, columns=[
        "component_desc",
        "factor",
        "J1",
        "J2",
        "J3",
        "J4",
        "J5",
        "J6",
        "J7",
        "J8",
        "J9",
        "ref",
        "scores_of_panel"
    ])\
        .replace("-", np.nan)\
        .replace("", np.nan)
    
    total_score = df.iloc[:-1]\
        .pipe(lambda x: x["scores_of_panel"].astype(float) * x["factor"].astype(float)).sum()

    parsed_score = float(df.iloc[-1]["scores_of_panel"])
    
    try:
        assert total_score - parsed_score < 0.1
    except Exception as e:
        print(total_score, parsed_score)
        print(df)
        raise e
    
    df = df.iloc[:-1].copy()
    # Removed because sometimes (or at least once), a number is actually missing:
    # assert df["element_num"].astype(int).tolist() == list(range(1, len(df) + 1))

    for i in range(9):
        colname = "J{}".format(i + 1)
        df[colname] = df[colname].astype(float)
    
    for colname in [ "factor", "scores_of_panel" ]:
        df[colname] = df[colname].astype(float)
            
    return df

def parse_page(page):
    rects = find_rects(page)
    if len(rects) == 0:
        raise EmptyResultsException

    assert len(rects) % 3 == 0
    results = []
    for i in range(len(rects) // 3):
        results.append({
            "metadata": parse_upper_rect(page, rects[i*3]).to_dict(),
            "elements": dictify(parse_elements(page, rects[i*3 + 1])),
            "components": dictify(parse_program_components(page, rects[i*3 + 2])),
        })
    return results
