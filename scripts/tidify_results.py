#!/usr/bin/env python3
import pandas as pd
import json
import glob
import hashlib
import sys
import os

def make_id(*strings):
    return hashlib.sha1("|".join(strings).encode("utf-8")).hexdigest()[:10]


class TidyResults(object):
    def __init__(self):
        self.programs = []
        self.performances = []
        self.judged_aspects = []
        self.judge_scores = []

    def merge(self, other_tidy):
        for attr in [ "programs", "performances", "judged_aspects", "judge_scores" ]:
            data = getattr(self, attr)
            data += getattr(other_tidy, attr)
            setattr(self, attr, data)
        return self

def tidify_competition(competition):
    """
    This function takes competition data, in the JSON 
    structure produced by parse_pdfs.py, and generates a
    "tidy" representation of that data.
    
    Cf. http://vita.had.co.nz/papers/tidy-data.html
    Cf. https://en.wikipedia.org/wiki/Tidy_data
    """

    tidy = TidyResults()
    
    pdf_path = competition["pdf"]
    sys.stderr.write("Tidying {}\n".format(pdf_path))

    # Note: All performances must come from the same competition
    competition_name = competition["performances"][0]["metadata"]["competition"]

    for i, p in enumerate(competition["performances"]):

        # Ensure that all performances in the same protocol refer to the same competition
        if p["metadata"]["competition"] != competition_name:
            raise ValueError("'{}' != '{}'".format(
                p["metadata"]["competition"],
                competition_name
            ))

        tidy.programs.append({
            "pdf": pdf_path,
            "competition": competition_name,
            "program": p["metadata"]["program"]
        })

        performance_id = make_id(
            competition_name,
            p["metadata"]["program"],
            p["metadata"]["name"]
        )

        p["metadata"]["performance_id"] = performance_id

        tidy.performances.append(dict(p["metadata"]))
        
        for section in [ "elements", "components" ]:
            
            for i, aspect in enumerate(p[section] or []):
                aspect_id = make_id(
                    performance_id,
                    section,
                    str(i),
                )

                a = {
                    "performance_id": performance_id,
                    "aspect_id": aspect_id,
                    "section": section,
                    "aspect_num": aspect.get("element_num", None),
                    "aspect_desc": aspect[section[:-1] + "_desc"],
                }

                a.update(dict((k, v) for k, v in aspect.items()
                    if k[0] != "J"
                    and k not in [ "component_desc", "element_desc", "element_num" ]))

                tidy.judged_aspects.append(a)

                for k, v in aspect.items():
                    if k[0] == "J":
                        tidy.judge_scores.append({
                            "aspect_id": aspect_id,
                            "judge": k,
                            "score": v
                        })
    return tidy

def tidify_competitions(list_of_competitions):
    tidy = TidyResults()
    for c in list_of_competitions:
        c_tidy = tidify_competition(c)
        tidy = tidy.merge(c_tidy)
    return tidy

def competitions_to_csvs(list_of_competitions, dest="."):
    tidy = tidify_competitions(list_of_competitions)

    programs_df = pd.DataFrame(tidy.programs)[[
            "competition",
            "program",
            "pdf",
        ]].sort_values([
            "competition",
            "program",
            "pdf"
        ]).drop_duplicates()


    performances_df = pd.DataFrame(tidy.performances)[[
            "performance_id",
            "competition",
            "program",
            "name",
            'nation',
            'rank',
            'starting_number',
            'total_segment_score',
            'total_element_score',
            'total_component_score',
            'total_deductions',
        ]].assign(
            starting_number=lambda x: x["starting_number"].astype(int)
        ).sort_values([
            "competition",
            "program",
            "starting_number"
        ])

    judged_aspects_df = pd.DataFrame(tidy.judged_aspects)[[
            "aspect_id",
            "performance_id",
            "section",
            "aspect_num",
            "aspect_desc",
            "info_flag",
            "credit_flag",
            "base_value",
            "factor",
            "goe",
            "ref",
            "scores_of_panel"
        ]].sort_values("aspect_id")

    judge_scores_df = pd.DataFrame(tidy.judge_scores)[[
            "aspect_id",
            "judge",
            "score"
        ]].dropna(subset=["score"])\
            .pipe(lambda x: x.sort_values(list(x.columns)))\
            .sort_values([
                "aspect_id",
                "judge"
            ])

    mkpath = lambda x: os.path.join(dest, x)

    programs_df.to_csv(
        mkpath("programs.csv"),
        index = False
    )

    performances_df.to_csv(
        mkpath("performances.csv"),
        index = False
    )

    judged_aspects_df.to_csv(
        mkpath("judged-aspects.csv"),
        index = False
    )

    judge_scores_df.to_csv(
        mkpath("judge-scores.csv"),
        index = False
    )

if __name__ == "__main__":
    competitions = [ json.load(open(path))
        for path in glob.glob("data/json/*.json") ]

    competitions_to_csvs(competitions, "data/tidy")
