from Analysis import analyzeMatch
import sys

inputData = sys.stdin.read().strip()

analyzeMatch(inputData, file=False).to_csv("Output/test.csv", index=False)