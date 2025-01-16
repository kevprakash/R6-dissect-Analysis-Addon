import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import matplotlib.pyplot as pt
import json
from Analysis import metaAnalysisMatches, timeSlots
import os


def visualize(jsonFiles: list[str], displayThreshold=0.04):
    mdf, s, o = metaAnalysisMatches(jsonFiles)

    atkSpawns, defSpawns = list(s[0]), list(s[1])
    atkOps, defOps = list(o[0]), list(o[1])

    for r in range(len(mdf)):
        row = mdf.iloc[r]
        ID = row.iloc[:2]
        roundCount = row.iloc[2]
        winRates = row.iloc[3:5].values
        pace = row["Pace"]
        kills = row["Kills"]
        killTimes = row.iloc[7:14].values
        plantStats = row.iloc[14:16].values
        spawnStats = row[atkSpawns].values
        opAStats = row[atkOps].values
        opDStats = row[defOps].values

        fig, ax = plt.subplots(2, 3)
        fig.suptitle(ID["Map"] + " : " + ID["Site"])

        def autopctAboveThreshold(pct):
            return f'{pct:.1f}%' if pct > displayThreshold * 100 else ''

        def statsAndLabels(stats, labels):
            total = sum(stats)
            filteredLabels = [(labels[i] if stats[i] / total > displayThreshold else '') for i in range(len(stats)) if stats[i] > 0]
            filteredStats = [x for x in stats if x > 0]
            merged = sorted(zip(filteredStats, filteredLabels))
            filteredStats, filteredLabels = zip(*merged)
            return list(filteredStats), list(filteredLabels)

        opAStats, opANames = statsAndLabels(opAStats, atkOps)
        ax[0, 0].pie(opAStats, labels=opANames, autopct=autopctAboveThreshold, rotatelabels=True)
        ax[0, 0].set_title("Attack Ops")

        opDStats, opDNames = statsAndLabels(opDStats, defOps)
        ax[0, 1].pie(opDStats, labels=opDNames, autopct=autopctAboveThreshold, rotatelabels=True)
        ax[0, 1].set_title("Defense Ops")

        ax[0, 2].pie(winRates, labels=["Attacker", "Defender"], autopct=autopctAboveThreshold, rotatelabels=True)
        ax[0, 2].set_title("Win Rates")

        ktInd = np.arange(len(killTimes))
        killTimes = list(reversed(killTimes[:-1])) + [killTimes[-1]]
        ts = list(reversed(timeSlots[:-3])) + [timeSlots[-3]]
        ax[1, 0].bar(ktInd, killTimes)
        ax[1, 0].set_xticks(ktInd)
        ax[1, 0].set_xticklabels(ts, rotation=90)
        ax[1, 0].set_title("Kill Timings")

        spawnStats, spawnNames = statsAndLabels(spawnStats, atkSpawns)
        ax[1, 1].pie(spawnStats, labels=spawnNames, autopct=autopctAboveThreshold, rotatelabels=True)
        ax[1, 1].set_title("Spawns")

        winCons = [plantStats[0] - plantStats[1], plantStats[1], 1 - plantStats[0]]
        ax[1, 2].pie(winCons, labels=["Plant", "Defuse", "Kill"], autopct=autopctAboveThreshold, rotatelabels=True)
        ax[1, 2].set_title("Win Conditions")

        fig.show()
    plt.show()


files = [f.path for f in os.scandir("R6 Dissect/Outputs") if not f.is_dir()]
visualize(files)