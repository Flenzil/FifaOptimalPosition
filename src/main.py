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
    rpp, areas = LoadPlayers(playerName, playerType, playerRating)
    allowedFormations = Restrictions(
        areas
    )  # Restrict the formations considered to just those that the input players fit.
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
    areas = {}
    for i in range(len(playerName)):
        rpp[playerName[i]], areas[playerName[i]] = FindPlayers(
            playerName[i], playerType[i], playerRating[i]
        )
    return rpp, areas


def FindPlayers(player_name, player_type, player_rating):
    """Returns ID of player given their name, card type and rating.
    If multiple players match, user is asked to specify which one they want.
    Exits if no player is found matching the criteria."""
    matches = []
    # Find players that match
    for i in range(INDEX[player_rating], INDEX[player_rating - 1]):
        line = linecache.getline("../player_info.csv", i)
        cols = line.split(",")

        if cols[7] == "":  # Players with no RPP (e.g GKs)
            continue

        rating_match = str(player_rating) == cols[2]
        if not rating_match:
            continue

        regex = [r"\b{}\b".format(x.lower()) for x in player_name.split(" ")]
        name_match = all([re.findall(x, cols[1].lower()) for x in regex])
        if not name_match:
            continue

        type_match = all(
            ([x.lower() in cols[6].lower() for x in player_type.split(" ")])
        )
        if not type_match:
            continue

        matches.append(cols)
    # Diffrienciate between duplicates
    if len(matches) > 1:
        print(
            "Did you mean {} who plays {} for {}? [0]".format(
                matches[0][1], matches[0][3], matches[0][5]
            )
        )
        for i in range(1, len(matches)):
            print("or")
            print(
                "Did you mean {} who plays {} for {}? [{}]".format(
                    matches[i][1], matches[i][3], matches[i][5], i
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

    area = [i for i in AREAS if match[3] in AREAS[i]][0]
    rpp = {
        POSITIONS[i]: int(float(match[i + 7]))
        for i in range(len(POSITIONS))
        if POSITIONS[i] in AREAS[area]
    }
    return rpp, area


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


def OptimisePositions(players, rpp, formation):
    """
    Returns a dictionary containing the formation and where each player should
    optimally play in that formation, maximising RPP. Also returns average RPP
    for this formation.
    """
    positionDict = {i: ["", 0] for i in formation}  # Create Blank dictionary to fill
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

        matches = re.findall(
            "{}[0-9]*".format(pos), formationString
        )  # Finds duplicate positions
        matchPlayers = [d[i] for i in matches]  # Finds the players in those positions

        rPlayer = rpp[player][pos]  # Rating for current player in current position
        rPlayerNext = NextBestPosRating(
            player, n, rpp, formationNoNums
        )  # Rating for current player in next best position
        diff = []

        for match in matchPlayers:
            rPlayerInPlace = rpp[match[0]][
                pos
            ]  # Rating for player already in this position
            rPlayerInPlaceNext = NextBestPosRating(
                match[0], match[1], rpp, formationNoNums
            )  # Rating for player already in this position in thier next best position

            avg1 = (rPlayerInPlace + rPlayerNext) / 2
            avg2 = (rPlayerInPlaceNext + rPlayer) / 2

            diff.append(avg1 - avg2)

        pos = matches[diff.index(min(diff))]  # Best position to proceed with
        matchPlayer = matchPlayers[diff.index(min(diff))][0]

        if min(diff) < 0:
            """
            Moves player in current position to thier next best position and
            places current player in current position
            """
            rank = d[pos][1]  # Player is in thier rankth best position.
            d[pos] = ["", 0]  # Clear position
            d, _ = PlacePlayer(
                d, player, re.sub("[0-9]", "", pos), formationString, n
            )  # Place player in position
            d = AllocatePlayers(
                d, matchPlayer, rpp, rank + 1, formation
            )  # Recursive call

            return d
        else:
            """
            Allocate current player to their next best position
            """
            AllocatePlayers(d, player, rpp, n + 1, formation)
            return d
    except KeyError:
        """
        Place current player in position
        """
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
    main()
