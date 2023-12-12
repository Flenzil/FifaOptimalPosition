import copy
from operator import ne
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

    print(rpp)
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
    """
    Restricts formations to only those that can support the inputted players
    Attemps to fill each formation with the input players. If a position cannot
    be filled by any player then the formation is invalid.
    """
    invalidFormations = []
    for formationName, formation in FORMATIONS.items():
        # Dictionary to contain filled positions.
        d = {position: "" for position in formation}
        players = copy.deepcopy(rpp)

        # Create a history list, which will contain the positions that a player
        # has visited while filling the team.
        for player in players:
            players[player]["history"] = []

        i = 0
        while True:
            # As long as there is an empty position in the team, keep looping through
            # players.
            position = formation[i % len(formation)]
            if d[position] == "":
                d = FillPosition(players, position, d)

            # Position unable to be filled
            if d == 0:
                invalidFormations.append(formationName)
                break

            # Team successfully filled
            if "" not in d.values():
                break
            i += 1

    allowedFormations = [i for i in FORMATIONS if i not in invalidFormations]

    if allowedFormations == []:
        raise SystemExit("Not a valid team!")

    return allowedFormations


def FillPosition(players, position, d):
    """
    Places player in position. If no player fits in position, then check already
    placed players to see if any of those could move to that position.
    """
    positionNoNums = re.sub("[0-9]", "", position)

    for playerName, playerPos in players.items():
        historyNoNums = [re.sub("[0-9]", "", i) for i in playerPos["history"]]
        if positionNoNums in playerPos and positionNoNums not in historyNoNums:
            # Place player in position
            d[position] = {playerName: playerPos}

            # If player has been moved from a previous position, empty that position
            # otherwise, remove player from list of unplaced players.
            if len(playerPos["history"]) > 0:
                d[playerPos["history"][-1]] = ""
            else:
                del players[playerName]

            # Add position to player history so they won't be placed there again.
            playerPos["history"].append(position)
            return d

    # If no player fits the position, check the already placed players that haven't already
    # been in that position at some point in their history.
    placedPlayers = {}
    for pos in d.keys():
        if d[pos] == "":
            continue
        for j in d[pos].values():
            historyNoNums = [re.sub("[0-9]", "", i) for i in j["history"]]
            if positionNoNums in j and positionNoNums not in historyNoNums:
                placedPlayers = placedPlayers | d[pos]

    # If no placed player matches either, then return 0 which is handled in Restrictions
    if placedPlayers == {}:
        return 0
    #
    # Recursive call to place player from list of eligible placed players.
    return FillPosition(placedPlayers, position, d)


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


def Displace(d, player, pos, n, formation):
    formationString = "".join(formation)

    d[pos + "1"] = ["", 0]  # Clear position

    # Place player in position
    d, _ = PlacePlayer(d, player, re.sub("[0-9]", "", pos), formationString, n)

    # Recrusive call
    return d


def PlayersInPosition(d, pos, rpp):
    regex = pos + "[0-9]*"

    playersInPosition = []
    for i in d.keys():
        try:
            match = re.search(regex, i).group()
            rating = rpp[d[match]][pos]
            playersInPosition.append(
                {d[match][0]: {"Position": match, "Rating": rating, "n": d[match][1]}}
            )
        except AttributeError:
            continue
    return playersInPosition


def AllocatePlayers(d, player, rpp, n, formation, force=False):
    """
    Fills a dictionary of positions : [players, n] such that the players are
    in their nth highest rpp. Attempts to place a  player in their best position
    unless there is another player better than them in that position.
    In that case, they are placed in their next best position until all
    players are placed.
    If force = True, the player cannot lose any matchups. This is used to resolve
    unresolvable collisions, where both players are in their loweest rated position.
    One of the players is then put back through this function with force = True.
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

    if len(rpp[player]) == 1:
        d = Displace(d, player, pos, n, formation)

        playersInPlace = PlayersInPosition(d, pos, rpp)
        playerInPlace = playersInPlace[0]
        name = list(playerInPlace[0].keys())[0]
        rating = playersInPlace[0]["Name"]
        for i in playersInPlace[1:]:
            if i["Rating"] < playerInPlace["Rating"]:
                name = list(i.keys())[0]
                rating = i["Rating"]

        return AllocatePlayers(d, name, rpp, rating + 1, formation)

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
            d = AllocatePlayers(d, player, rpp, n + 1, formation, force=force)
            return d

        # Rating for current player in current position
        rPlayer = rpp[player][pos]
        if force:
            rPlayer = 1000
            force = False

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

            if rPlayerNext == -1000 and rPlayerInPlaceNext == -1000:
                n = PrevBestPos(player, n, rpp, formationNoNums)
                d = AllocatePlayers(d, player, rpp, n, formation, force=True)
                return d

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
            d = AllocatePlayers(d, matchPlayer, rpp, rank + 1, formation, force=force)
            return d
        else:
            # Allocate current player to their next best position
            AllocatePlayers(d, player, rpp, n + 1, formation, force=force)
            return d
    except KeyError:
        # Place current player in position
        d, _ = PlacePlayer(d, player, pos, formationString, n)
        return d


def PrevBestPos(player, n, rpp, formation):
    """
    Returns players previous best positional rating that exists in the current
    formation.
    """
    m = n - 1
    nextBestPos = NthBestPos(player, rpp, m)
    while nextBestPos not in formation:
        m = m - 1
        nextBestPos = NthBestPos(player, rpp, m)
    return m


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
