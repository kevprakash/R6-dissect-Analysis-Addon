import pandas as pd
import numpy as np
import json

pd.options.display.max_columns = None

idCols = ["Player ID", "Match ID", "Round Number"]
statCols = ["Kills", "Assists", "Deaths", "Headshots", "KOST",
            "Pivot Kills", "Pivot Deaths", "Opening Kills", "Opening Deaths",
            "Trade Kills", "Traded Kills", "Traded Deaths", "Objective", "Wins", "Losses"]


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


def findTeamStats(dataFile: str, teamIDs: dict[str, str]):
    df = pd.read_csv(dataFile)

    df.loc[df["Player ID"].isin(teamIDs.keys()), "Player ID"] = df.loc[df["Player ID"].isin(teamIDs.keys()), "Player ID"].replace(teamIDs)

    return df[df["Player ID"].isin(teamIDs.values())].iloc[:, 1:].reset_index(drop=True)