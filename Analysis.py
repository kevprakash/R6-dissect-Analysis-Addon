from pprint import pprint

import pandas as pd
import numpy as np
import json

pd.options.display.max_columns = None

idCols = ["Player ID", "Match ID", "Round Number"]
statCols = ["Kills", "Assists", "Deaths", "Headshots", "KOST",
            "Pivot Kills", "Pivot Deaths", "Opening Kills", "Opening Deaths",
            "Trade Kills", "Traded Kills", "Traded Deaths", "Objective", "Wins", "Losses"]
timeSlots = ["<30s", "30-60s", "60-90s", "90-120s", "120-150s", "150-180s", "Post-Plant", "Plant", "Defuse"]


def analyzeMatches(jsons: list[str], shouldCompile=True):
    dfs = []
    for j in jsons:
        dfs.append(analyzeMatch(j, file=True, shouldCompile=False))

    totalDF = pd.concat(dfs, ignore_index=True)
    if shouldCompile:
        sumStats = totalDF[["Player ID"] + statCols]

        sumStats = sumStats.groupby("Player ID").sum().reset_index(drop=False)
        compiledStats = compileStats(sumStats)

        return compiledStats
    else:
        return totalDF


def analyzeMatch(jsonData: str, file=True, shouldCompile=True):
    if file:
        with open(jsonData, 'r') as f:
            data = json.load(f)
    else:
        data = json.loads(jsonData)

    rounds = data["rounds"]

    # print(json.dumps(data, indent=4))

    roundDFs = []
    for r in rounds:
        roundDFs.append(analyzeRound(r))
        # print("-" * 10)

    # print(json.dumps(rounds[4], indent=4))

    totalDF = pd.concat(roundDFs, ignore_index=True)

    if shouldCompile:
        sumStats = totalDF[["Player ID"] + statCols]

        sumStats = sumStats.groupby("Player ID").sum().reset_index(drop=False)
        compiledStats = compileStats(sumStats)

        return compiledStats
    else:
        return totalDF


def analyzeRound(r):
    matchID = r["matchID"]
    roundNumber = r["roundNumber"]
    score = (r["teams"][0]["startingScore"], r["teams"][1]["startingScore"])
    usernameToID = {}
    IDToTeam = {}
    aliveCounts = [0, 0]
    teamWin = (r["teams"][0]["won"], r["teams"][1]["won"])

    if teamWin[0] == teamWin[1]:
        if "winCondition" in r["teams"][0]:
            teamWin = (True, False)
        else:
            teamWin = (False, True)

    for player in r["players"]:
        playerID = player["profileID"]
        usernameToID[player["username"]] = playerID
        teamIndex = player["teamIndex"]
        IDToTeam[playerID] = teamIndex
        aliveCounts[teamIndex] += 1

    killEvents = []
    planter = None
    defuser = None

    first = True
    for event in r["matchFeedback"]:
        if event["type"]["name"].lower() == "defuserplantcomplete":
            planter = usernameToID[event["username"]]

        elif event["type"]["name"].lower() == "kill":
            # print(event)
            killEvents.append({
                "killer": usernameToID[event["username"]],
                "target": usernameToID[event["target"]],
                "headshot": 1 if event["headshot"] else 0,
                "pivotKill": 0,
                "isTrade": 0,
                "traded": 0,
                "openingKill": 1 if first else 0,
                "openingDeath": 1 if first else 0,
                "time": event["timeInSeconds"]
            })

        first = False

    potentialPivots = []
    playerDelta = aliveCounts[0] - aliveCounts[1]
    potentialTrades = []
    tradeWindowTime = 10

    for i in range(len(killEvents)):
        deathTeam = IDToTeam[killEvents[i]["target"]]
        deltaDir = -1 if deathTeam == 0 else 1
        playerDelta += deltaDir

        # Check if this kill trades out another kill
        indicesToDelete = []
        killTime = killEvents[i]["time"]
        for j in range(len(potentialTrades)):
            kill = potentialTrades[j]
            if kill["time"] > killTime + tradeWindowTime:
                indicesToDelete.append(j)
            elif kill["killer"] == killEvents[i]["target"]:
                killEvents[i]["isTrade"] = 1
                kill["traded"] += 1
                indicesToDelete.append(j)

        for j in reversed(indicesToDelete):
            del potentialTrades[j]

        potentialTrades.append(killEvents[i])

        if (playerDelta == 0) or (playerDelta == deltaDir):
            killEvents[i]["pivotKill"] = 1
            for kill in potentialPivots:
                kill["pivotKill"] = 1
            potentialPivots = []

        if ((deathTeam == 0) and (playerDelta < -1)) or ((deathTeam == 1) and (playerDelta > 1)):
            potentialPivots.append(killEvents[i])

    df = pd.DataFrame(columns=idCols + statCols)

    for ID in IDToTeam.keys():
        ID_ID = [ID, matchID, roundNumber]
        IDStats = [0 for _ in range(len(statCols))]

        IDRow = ID_ID + IDStats
        df.loc[len(df)] = IDRow

        # print(teamWin)

        if teamWin[IDToTeam[ID]]:
            df.loc[df["Player ID"] == ID, "Wins"] += 1
        else:
            df.loc[df["Player ID"] == ID, "Losses"] += 1

    # print()

    if planter is not None:
        df.loc[df["Player ID"] == planter, "Objective"] = 1
        df.loc[df["Player ID"] == planter, "KOST"] = 1

    if defuser is not None:
        df.loc[df["Player ID"] == defuser, "Objective"] = 1
        df.loc[df["Player ID"] == defuser, "KOST"] = 1

    for kill in killEvents:
        # print(kill)
        df.loc[df["Player ID"] == kill["killer"], "Kills"] += 1
        df.loc[df["Player ID"] == kill["killer"], "KOST"] = 1
        df.loc[df["Player ID"] == kill["killer"], "Headshots"] += kill["headshot"]
        df.loc[df["Player ID"] == kill["killer"], "Pivot Kills"] += kill["pivotKill"]
        df.loc[df["Player ID"] == kill["killer"], "Opening Kills"] += kill["openingKill"]
        df.loc[df["Player ID"] == kill["killer"], "Trade Kills"] += kill["isTrade"]
        df.loc[df["Player ID"] == kill["killer"], "Traded Kills"] += kill["traded"]

        df.loc[df["Player ID"] == kill["target"], "Deaths"] += 1
        df.loc[df["Player ID"] == kill["target"], "Pivot Deaths"] += kill["pivotKill"]
        df.loc[df["Player ID"] == kill["target"], "Opening Deaths"] += kill["openingKill"]
        df.loc[df["Player ID"] == kill["target"], "Traded Deaths"] += kill["traded"]
        if kill["traded"] > 0:
            df.loc[df["Player ID"] == kill["target"], "KOST"] = 1

    for ID in IDToTeam.keys():
        # print(df.loc[df["Player ID"] == ID, "Deaths"])
        if df.loc[df["Player ID"] == ID, "Deaths"].values[0] == 0:
            df.loc[df["Player ID"] == ID, "KOST"] = 1

    return df


def compileStats(df):

    df["HS%"] = df["Headshots"] / np.where(df['Kills'] < 1, 1, df['Kills']) * 100
    df["KOST"] = df["KOST"] / (df["Wins"] + df["Losses"])

    for prefix in ["", "Pivot ", "Opening "]:
        df[prefix + 'K/D'] = df[prefix + 'Kills'] / np.where(df[prefix + 'Deaths'] < 1, 1, df[prefix + 'Deaths'])
        df[prefix + '+/-'] = df[prefix + "Kills"] - df[prefix + "Deaths"]

    for prefix in ["Traded "]:
        df[prefix + 'D/K'] = df[prefix + 'Deaths'] / np.where(df[prefix + 'Kills'] < 1, 1, df[prefix + 'Kills'])
        df[prefix + '+/-'] = df[prefix + "Deaths"] - df[prefix + "Kills"]

    df["Untraded Kill Ratio"] = (df["Kills"] - df["Traded Kills"]) / np.where(df["Kills"] < 1, 1, df["Kills"])
    df["Traded Death Ratio"] = df["Traded Deaths"] / np.where(df["Deaths"] < 1, 1, df["Deaths"])

    return df


def metaAnalysisMatch(jsonData: str):
    with open(jsonData, 'r') as f:
        data = json.load(f)

    # pprint(data)

    compiledStats = {
        "Map": [],
        "Site": [],
        "Attacker Win": [],
        "Defender Win": [],
        "<30s": [],
        "30-60s": [],
        "60-90s": [],
        "90-120s": [],
        "120-150s": [],
        "150-180s": [],
        "Post-Plant": [],
        "Plant": [],
        "Defuse": []
    }

    operators = set(), set()    # ATK, DEF
    spawns = set(), set()       # ATK, DEF

    for i in range(len(data["rounds"])):
        r = data["rounds"][i]
        players = r["players"]
        gameMap = r['map']['name']
        site = r['site']
        teams = r['teams']

        firstAttack = teams[0]['role'] == 'Attack'

        compiledStats["Map"].append(gameMap)
        compiledStats["Site"].append(site)

        for p in players:
            operator = p['operator']['name']
            spawn = p['spawn']
            isTeam1 = p['teamIndex'] == 0

            opPool = operators[0] if (firstAttack == isTeam1) else operators[1]
            spawnPool = spawns[0] if (firstAttack == isTeam1) else spawns[1]

            opPool.add(operator)
            spawnPool.add(spawn)

            if operator in compiledStats.keys():
                o = compiledStats[operator]
                while len(o) <= i:
                    o.append(0)
                o[-1] += 1
            else:
                compiledStats[operator] = [0 for _ in range(i)] + [1]

            if spawn in compiledStats.keys():
                s = compiledStats[spawn]
                while len(s) <= i:
                    s.append(0)
                s[-1] += 1
            else:
                compiledStats[spawn] = [0 for _ in range(i)] + [1]

        for o in operators[0].union(operators[1]):
            while len(compiledStats[o]) <= i:
                compiledStats[o].append(0)

        for s in spawns[0].union(spawns[1]):
            while len(compiledStats[s]) <= i:
                compiledStats[s].append(0)

        atkWin = False
        defWin = False
        winCondition = None
        for t in r["teams"]:
            if t["won"]:
                if t["role"] == 'Attack':
                    atkWin = True
                else:
                    defWin = True
                if 'winCondition' in t.keys():
                    winCondition = t['winCondition']

        if atkWin and defWin:
            if winCondition == 'DisabledDefuser':
                compiledStats["Attacker Win"].append(0)
                compiledStats["Defender Win"].append(1)
            elif winCondition == 'DefusedBomb':
                compiledStats["Attacker Win"].append(1)
                compiledStats["Defender Win"].append(0)
        else:
            if atkWin:
                compiledStats["Attacker Win"].append(1)
                compiledStats["Defender Win"].append(0)
            elif defWin:
                compiledStats["Attacker Win"].append(0)
                compiledStats["Defender Win"].append(1)

        for t in timeSlots:
            compiledStats[t].append(0)

        postPlant = False
        for feedback in r['matchFeedback']:
            if feedback['type']['id'] == 3:
                postPlant = True
                compiledStats["Plant"][-1] += 1
            elif feedback['type']['id'] == 5:
                compiledStats['Defuse'][-1] += 1
            elif feedback['type']['id'] == 0:
                if postPlant:
                    compiledStats["Post-Plant"][-1] += 1
                else:
                    killTime = feedback['timeInSeconds']
                    if killTime < 30:
                        compiledStats["<30s"][-1] += 1
                    elif killTime < 60:
                        compiledStats["30-60s"][-1] += 1
                    elif killTime < 90:
                        compiledStats["60-90s"][-1] += 1
                    elif killTime < 120:
                        compiledStats["90-120s"][-1] += 1
                    elif killTime < 150:
                        compiledStats["120-150s"][-1] += 1
                    else:
                        compiledStats["150-180s"][-1] += 1

    # pprint(compiledStats)

    df = pd.DataFrame(compiledStats)
    df = df[["Map", "Site", "Attacker Win", "Defender Win"] + timeSlots + list(spawns[0].union(spawns[1])) + list(operators[0].union(operators[1]))]

    return df, spawns, operators


def metaAnalysisMatches(jsons: list[str]):
    dfs = []
    spawns = set(), set()
    operators = set(), set()
    for j in jsons:
        d, s, o = metaAnalysisMatch(j)
        dfs.append(d)
        spawns[0].update(s[0])
        spawns[1].update(s[1])
        operators[0].update(o[0])
        operators[1].update(o[1])
        # print(len(dfs[-1]))

    totalDF = pd.concat(dfs, axis=0)
    totalDF.fillna(0, inplace=True)

    # print(totalDF)

    grouped = totalDF.groupby(["Map", "Site"])
    totalDF = grouped.mean()
    totalDF["Rounds"] = grouped.size()

    columns = list(totalDF.columns)
    columns.insert(0, columns.pop(-1))
    totalDF = totalDF[columns].reset_index()

    timeSlots = ["<30s", "30-60s", "60-90s", "90-120s", "120-150s", "150-180s", "Post-Plant", "Plant", "Defuse"]

    paceDF = totalDF[["Map", "Site"] + ["<30s", "30-60s", "60-90s", "90-120s", "120-150s", "150-180s"]].copy()
    paceMatrix = paceDF.groupby(["Map", "Site"]).sum().values
    paceWeights = np.array([30, 60, 90, 120, 150, 180])[:, None] / 180
    paceKills = paceMatrix @ np.ones((paceMatrix.shape[-1], 1))
    paceMatrix = paceMatrix @ paceWeights / paceKills
    totalDF.loc[:, "Pace"] = paceMatrix
    totalDF.loc[:, "Kills"] = paceKills

    totalDF = totalDF[["Map", "Site", "Rounds", "Attacker Win", "Defender Win", "Pace", "Kills"] + timeSlots + list(spawns[0].union(spawns[1])) + list(operators[0].union(operators[1]))]

    return totalDF, spawns, operators


def findTeamStats(dataFile: str, teamIDs: dict[str, str]):
    df = pd.read_csv(dataFile)

    df.loc[df["Player ID"].isin(teamIDs.keys()), "Player ID"] = df.loc[df["Player ID"].isin(teamIDs.keys()), "Player ID"].replace(teamIDs)

    return df[df["Player ID"].isin(teamIDs.values())].iloc[:, 1:].reset_index(drop=True)


def nameFinder(jsons: list[str]):
    idToName = {}
    for j in jsons:
        with open(j, 'r') as f:
            data = json.load(f)
            # pprint(data)
            for r in data["rounds"]:
                for p in r['players']:
                    ID = p['profileID']
                    userName = p['username']

                    if ID in idToName.keys():
                        idToName[ID].add(userName)
                    else:
                        idToName[ID] = {userName}

    return idToName