from pprint import pprint
import os
from Analysis import findTeamStats, metaAnalysisMatches, metaAnalysisMatch, nameFinder

teamIDs = {
    "8dcdbff1-df5e-4a6c-8293-98309780052e": "Kevin",
    "2acd7f59-f120-4a5c-b835-58d97e352704": "Matt",
    "6e4995c3-a529-4710-96b3-4d1c2fe12fcd": "Char",
    "714ebca1-bb1d-4fba-9eb7-1b3a6cd9ea6f": "Jake",
    "827fb2a0-833a-43af-900e-8a50ae39de5f": "Navdip",
}

print(findTeamStats("Output/Analysis.csv", teamIDs))

jsonFiles = [f.path for f in os.scandir("R6 Dissect/Outputs") if not f.is_dir()]

# pprint(nameFinder(jsonFiles))
