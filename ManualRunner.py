import numpy as np
import pandas as pd
import os
from Analysis import findTeamStats, metaAnalysisMatches, metaAnalysisMatch

teamIDs = {
    "8dcdbff1-df5e-4a6c-8293-98309780052e": "Frickin H3ck",
}

# print(findTeamStats("Output/Results.csv", teamIDs))
# print(pd.read_csv("Output/Results.csv").iloc[:, 2:].mean())

jsonFiles = [f.path for f in os.scandir("R6 Dissect/Outputs") if not f.is_dir()]

meta, s, o = metaAnalysisMatch(jsonFiles[0])
print(o[0])
print(o[1])
