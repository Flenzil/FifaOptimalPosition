import copy
import time
import linecache
import re
import pandas as pd

FORMATIONS = pd.read_csv("../formations.csv")

AREAS = {
    i: [j for j in pd.read_csv("../areas.csv")[i] if j == j]
    for i in pd.read_csv("../areas.csv")
}

INDEX = pd.read_csv("../index.csv")
INDEX = {
    INDEX["Rating"].tolist()[i]: INDEX["Unnamed: 0"].tolist()[i]
    for i in range(len(INDEX))
}
POSITIONS = [
    "ST",
    "RW",
    "LW",
    "CF",
    "CAM",
    "CM",
    "RM",
    "LM",
    "CDM",
    "CB",
    "LB",
    "LWB",
    "RB",
    "RWB",
]


def main():
    dfplayers = pd.read_csv("../players.csv")

    playerName = dfplayers["Players"]
    playerRating = dfplayers["Player Ratings"]
    playerType = dfplayers["Player Type"]

    rpp = LoadPlayers(playerName, playerType, playerRating)

    # Restrict the formations considered to just those that the input players fit.
    allowedFormations = Restrictions(rpp)
    print(allowedFormations)

    teams = {}
    average_rpp = {}

    for i in allowedFormations:
        teams[i], average_rpp[i] = OptimisePositions(playerName, rpp, FORMATIONS[i])

    optimalFormation = max(zip(average_rpp.values(), average_rpp.keys()))[1]

    print()
    print("===========Optimal Formation:", optimalFormation, "============")
    print()
    for i in teams[optimalFormation].items():
        print(re.sub("[0-9]", "", i[0]), ":", i[1])


def LoadPlayers(playerName, playerType, playerRating):
    rpp = {}
    for i in range(len(playerName)):
        rpp[playerName[i]] = FindPlayers(playerName[i], playerType[i], playerRating[i])
    return rpp


def FindPlayers(player_name, player_type, player_rating):
    """Returns ID of player given their name, card type and rating.
    If multiple players match, user is asked to specify which one they want.
    Exits if no player is found matching the criteria."""
    matches = []
    # Find players that match
    for i in range(INDEX[player_rating], INDEX[player_rating - 1]):
        line = linecache.getline("../player_info.csv", i)
        cols = line.split(",")

        if cols[10] == "":  # Players with no RPP (e.g GKs)
            continue

        rating_match = str(player_rating) == cols[2]
        if not rating_match:
            continue

        regex = [r"\b{}\b".format(x.lower()) for x in player_name.split(" ")]
        name_match = all([re.findall(x, cols[1].lower()) for x in regex])
        if not name_match:
            continue

        type_match = all(
            ([x.lower() in cols[9].lower() for x in player_type.split(" ")])
        )
        if not type_match:
            continue

        matches.append(cols)
    # Diffrienciate between duplicates
    if len(matches) > 1:
        print(
            "Did you mean {} who plays {} for {}? [0]".format(
                matches[0][1], matches[0][3], matches[0][8]
            )
        )
        for i in range(1, len(matches)):
            print("or")
            print(
                "Did you mean {} who plays {} for {}? [{}]".format(
                    matches[i][1], matches[i][3], matches[i][8], i
                )
            )
        print()
        while True:
            try:
                user = int(input("Enter selection: "))
                matches[user]
                break
            except (ValueError, IndexError):
                continue

        match = matches[user]
    else:
        try:
            match = matches[0]
        except IndexError:
            raise SystemExit(
                "There is no {} {} rated player named {}!".format(
                    player_type, player_rating, player_name.capitalize()
                )
            )
    pos = match[2:7]

    rpp = {
        POSITIONS[i]: int(float(match[i + 10]))
        for i in range(len(POSITIONS))
        if POSITIONS[i] in pos
    }
    return rpp


def AreasInFormation():
    """
    For every formation in FORMATIONS, counts the number of positions in each
    area in AREAS.

    Returns dictionary of dictionaries in the format

    formation : {area : count}
    """
    areasInFormation = {}
    for formationName, formation in FORMATIONS.items():
        areasInFormation[formationName] = {}

        for position in formation:
            for areaName, area in AREAS.items():
                if re.sub("[0-9]", "", position) in area:
                    try:
                        areasInFormation[formationName][areaName] += 1
                    except KeyError:
                        areasInFormation[formationName][areaName] = 1

    return areasInFormation


def Restrictions(rpp):
    invalidFormations = []
    for formationName, formation in FORMATIONS.items():
        d = {position: "" for position in formation}
        players = copy.deepcopy(rpp)
        for player in players:
            players[player]["history"] = []
        i = 0
        while True:
            position = formation[i % len(formation)]
            if d[position] == "":
                d = FillPosition(players, position, d)
            if d == 0:
                invalidFormations.append(formationName)
                break
            if len(players) == 0:
                break
            i += 1
    allowedFormations = [i for i in FORMATIONS if i not in invalidFormations]
    return allowedFormations


def FillPosition(players, position, d):
    positionNoNums = re.sub("[0-9]", "", position)
    for playerName, playerPos in players.items():
        if positionNoNums in playerPos and positionNoNums not in playerPos["history"]:
            d[position] = {playerName: playerPos}

            if len(playerPos["history"]) > 0:
                d[playerPos["history"][-1]] = ""
            else:
                del players[playerName]
            playerPos["history"].append(positionNoNums)

            return d
    placedPlayers = {}
    for i in d.values():
        if i != "" and position in i.keys() and position not in i["history"]:
            placedPlayers = placedPlayers | i
    if placedPlayers == {}:
        return 0
    return FillPosition(placedPlayers, position, d)


'''
def Restrictions(areas):
    """
    Returns the valid formations given the team inputted by the user. So if
    the input team has 2 CBs then any formation that requires 3 CB is invalid.
    """
    areasInFormation = (
        AreasInFormation()
    )  # Number of positions in each area for every for

    playerAreas = {}  # Number of positions in each area for input formation
    for i in areas.values():
        try:
            playerAreas[i] += 1
        except KeyError:
            playerAreas[i] = 1

    """
    Check if number of positions in the each area of each formation is
    the same as the number of positions in each area of the input formation.
    So if the input formation has 4 central players, reject all formations that
    have !4 central players.
    """
    allowedFormations = []
    match = 0
    for item in areasInFormation.items():
        formationName = item[0]
        formation = item[1]
        for area in playerAreas:
            match = 1
            try:
                if playerAreas[area] != formation[area]:
                    match = 0
                    break
            except KeyError:
                match = 0
                break
        if match:
            allowedFormations.append(formationName)

    if len(allowedFormations) == 0:
        raise Exception("Invalid Team!")

    return allowedFormations
'''


def OptimisePositions(players, rpp, formation):
    """
    Returns a dictionary containing the formation and where each player should
    optimally play in that formation, maximising RPP. Also returns average RPP
    for this formation.
    """
    positionDict = {i: ["", 0] for i in formation}  # Create Blank dictionary to fill

    # List of players that cannot be moved, they are in their lowest rated position

    for i in players:
        positionDict = AllocatePlayers(positionDict, i, rpp, 0, formation)
    positionDict = {
        pos: player[0] for pos, player in positionDict.items()
    }  # Strips position ranking

    avg = sum(
        [rpp[player][re.sub("[0-9]", "", pos)] for pos, player in positionDict.items()]
    ) / len(
        positionDict
    )  # Average rpp for formation

    return positionDict, avg


def AllocatePlayers(d, player, rpp, n, formation):
    """
    Fills a dictionary of positions : [players, n] such that the players are
    in their nth highest rpp. Attempts to place a  player in their best position
    unless there is another player better than them in that position.
    In that case, they are placed in their next best position until all
    players are placed.
    """
    formationNoNums = [re.sub(r"[0-9]+", "", i) for i in formation]
    formationString = "".join(formation)

    pos = NthBestPos(player, rpp, n)
    while pos not in formationNoNums:
        n = n + 1
        pos = NthBestPos(player, rpp, n)
    d, code = PlacePlayer(d, player, pos, formationString, n)
    if code == 0:  # Player was placed successfully
        return d

    # Player was not placed and there are duplicate positions that are all filled.
    try:
        """
        Formations can have multiples of the same position, i.e CM1, CM2. We find
        these repeat formations and proceed with the position that gives results
        in the biggest increase to average rpp when swapped with the current
        player.
        """
        # Finds duplicate positions
        matches = re.findall("{}[0-9]*".format(pos), formationString)

        # Finds names of players in the duplicate positions but makes sure that they
        # are not currently in their lowest rated position, which means they wouldn't
        # be able to move and so shouldn't be considered.
        matchPlayers = []
        for i in matches:
            if d[i][1] < len(rpp[d[i][0]]):
                matchPlayers.append(d[i])

        # If no matches survive the above, then move on to the current players next
        # best position.
        if len(matchPlayers) == 0:
            d = AllocatePlayers(d, player, rpp, n + 1, formation)
            return d

        # Rating for current player in current position
        rPlayer = rpp[player][pos]

        # Rating for current player in their next best position. If there is no next
        # best position (IndexError from NextBestPosRating function), then set rating
        # to some low number so that it will always lose matchups.
        try:
            rPlayerNext = NextBestPosRating(player, n, rpp, formationNoNums)
        except IndexError:
            rPlayerNext = -1000

        diff = []
        for match in matchPlayers:
            # Rating for player already in this position
            rPlayerInPlace = rpp[match[0]][pos]
            # Rating for player already in this position in thier next best position
            # As before, a very low number is used if there is no next best position.
            try:
                rPlayerInPlaceNext = NextBestPosRating(
                    match[0], match[1], rpp, formationNoNums
                )
            except IndexError:
                rPlayerInPlaceNext = -1000

            avg1 = (rPlayerInPlace + rPlayerNext) / 2
            avg2 = (rPlayerInPlaceNext + rPlayer) / 2

            diff.append(avg1 - avg2)

        pos = matches[diff.index(min(diff))]  # Best position to proceed with
        matchPlayer = matchPlayers[diff.index(min(diff))][0]

        if min(diff) < 0:
            # Moves player in current position to thier next best position and
            # places current player in current position
            rank = d[pos][1]  # Player is in thier rankth best position.
            d[pos] = ["", 0]  # Clear position

            # Place player in position
            d, _ = PlacePlayer(d, player, re.sub("[0-9]", "", pos), formationString, n)

            # Recrusive call
            d = AllocatePlayers(d, matchPlayer, rpp, rank + 1, formation)
            return d
        else:
            # Allocate current player to their next best position
            AllocatePlayers(d, player, rpp, n + 1, formation)
            return d
    except KeyError:
        # Place current player in position
        d, _ = PlacePlayer(d, player, pos, formationString, n)
        return d


def NextBestPosRating(player, n, rpp, formation):
    """
    Returns players next best positional rating that exists in the current
    formation.
    """
    m = n
    nextBestPos = NthBestPos(player, rpp, m + 1)
    while nextBestPos not in formation:
        m = m + 1
        nextBestPos = NthBestPos(player, rpp, m)
    return rpp[player][nextBestPos]


def PlacePlayer(d, player, pos, formationString, n):
    """
    Places player in dictionary d while accounting for any trailing numbers
    that the keys in d might have. Checks if position is already filled.
    In addition to returning the dictionary, returns a 0 to indicate successful
    placement or 1 to indicate no placement i.e all positions already occupied.
    """
    try:
        if d[pos] == ["", 0]:
            d[pos] = [player, n]
            return d, 0
        else:
            return d, 1

    except KeyError:
        posWithNums = re.findall("{}[0-9]*".format(pos), formationString)

        for i in posWithNums:
            if d[i] == ["", 0]:
                d[i] = [player, n]
                return d, 0

        return d, 1


def NthBestPos(player, rpp, n):
    # Returns the position with the players nth highest rpp
    sortedPositions = sorted(
        rpp[player], key=rpp[player].get, reverse=True
    )  # Sorts positions for this player from highest to lowest rpp
    return sortedPositions[n]


if __name__ == "__main__":
    start = time.time()
    main()
    print(time.time() - start)
