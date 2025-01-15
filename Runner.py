import subprocess
import sys
import os
from Analysis import analyzeMatches


def run_program():
    targetDirectory = sys.argv[1] if len(sys.argv) > 1 else "R6 Dissect/Matches"

    matches = [f.path for f in os.scandir(targetDirectory) if f.is_dir()]

    for match in matches:
        matchName = match.split("\\")[-1]
        cmd = ["R6 Dissect/r6-dissect.exe", match, "-o", "R6 Dissect/Outputs/" + matchName + ".json"]
        subprocess.run(cmd)

    jsonFiles = [f.path for f in os.scandir("R6 Dissect/Outputs") if not f.is_dir()]
    df = analyzeMatches(jsonFiles, shouldCompile=True)
    df.to_csv("Output/Results.csv")


if __name__ == "__main__":
    run_program()