import urllib3 as ul
import numpy as np
import unicodedata
import re
import pandas as pd

FORMATIONS = pd.read_csv("FORMATIONS.csv")

AREAS = {
    i: [j for j in pd.read_csv("AREAS.csv")[i] if j == j]
    for i in pd.read_csv("AREAS.csv")
}


def main():
    dfplayers = pd.read_csv("players.csv")

    players = dfplayers["Players"]
    playerRating = dfplayers["Player Ratings"]

    rpp, areas = LoadPlayers(
        players, playerRating
    )  # Load ratings per position and the area that the players position belongs to.

    allowedFormations = Restrictions(
        areas
    )  # Restrict the formations considered to just those that the input players fit.
    teams = {}
    average_rpp = {}

    for i in allowedFormations:
        teams[i], average_rpp[i] = OptimisePositions(players, rpp, FORMATIONS[i])

    optimalFormation = max(zip(average_rpp.values(), average_rpp.keys()))[1]

    print()
    print("===========Optimal Formation:", optimalFormation, "============")
    print()
    for i in teams[optimalFormation].items():
        print(re.sub("[0-9]", "", i[0]), ":", i[1])


def LoadPlayers(players, playerRating):
    try:
        dfrpp = pd.read_csv("dfrpp.csv")
        dfareas = pd.read_csv("dfareas.csv")

        areas = {dfareas["Unnamed: 0"][i]: dfareas["0"][i] for i in range(len(dfareas))}

        rpp = {}
        for i in dfrpp:
            if i == "Unnamed: 0":
                continue

            rpp[i] = {
                dfrpp["Unnamed: 0"][j]: dfrpp[i][j].astype(int)
                for j in range(len(dfrpp[i]))
                if not np.isnan(dfrpp[i][j])
            }
        return rpp, areas

    except FileNotFoundError:
        rpp = {}
        areas = {}
        for i in range(len(players)):
            rpp[players[i]], areas[players[i]] = RPP(players[i], playerRating[i])

        dfrpp = pd.DataFrame(rpp)
        dfrpp.to_csv("dfrpp.csv")

        dfareas = pd.DataFrame.from_dict(areas, orient="index")
        dfareas.to_csv("dfareas.csv")

        return rpp, areas


def strip_accents(s):
    # Anglicises foreign names
    return "".join(
        c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn"
    )


def RPP(player, playerRating):
    """
    Returns dictionary containing ratings per position for player of rating playerRating.
    On FUTbin, players have a unique ID number that prevents us from accessing
    their page directly. Instead, the search page is loaded (hopefully with only
    a single search result) and the player page is accessed that way.
    """

    user_agent = "Mozilla/5.0"
    headers = {
        "User-Agent": user_agent,
    }
    # ======================================== Produces text file for search page =================================================
    url = "https://www.futbin.com/24/players?page=1&player_rating={0}-{0}&search={1}".format(
        playerRating, player.replace(" ", "%20")
    )
    http = ul.PoolManager()
    request = http.request("GET", url, headers=headers)
    searchdata = request.data.decode("utf-8")

    # ============================================= Finds player ID number ========================================================
    start = searchdata.find("/24/player/") + len("/24/player/")
    tmp = searchdata[start : start + 30]

    end = tmp.find("/")
    playernum = tmp[:end]

    # ======================================== Produces text file for player page =================================================

    url = "https://www.futbin.com/24/player/{0}/{1}/".format(
        playernum, player[max(player.find(" ") + 1, 0) :]
    )
    request = http.request("GET", url, headers=headers)
    pagedata = request.data.decode("utf-8")

    # ==================================== Produces Rating per Position for player ================================================
    start = pagedata.find("rpp_field_pos")
    end = start + pagedata[start:].find("m_box_chem_p_filters")
    dataRelavant = pagedata[start:end]

    player_area = Area(pagedata)
    pos = AREAS[player_area]

    start = []
    for i in range(len(pos)):
        tmp = dataRelavant.find('rpp_position">{0}'.format(pos[i]))
        start.append(dataRelavant[tmp:].find("rpp_rating") + 12 + tmp)

    rpp = {
        pos[i]: int(dataRelavant[start[i] : start[i] + 2]) for i in range(len(start))
    }

    return rpp, player_area


def Area(pagedata):
    """
    Finds what area of the pitch the player plays on so that LB cannot move to RB for example
    """

    start = pagedata.find("&position=") + 10

    end = pagedata[start:].find('"')
    pos = pagedata[start : start + end]

    area = [i for i in AREAS if pos in AREAS[i]][0]
    return area


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
            d[pos] = ["", 0]  # Clear position
            d, _ = PlacePlayer(
                d, player, re.sub("[0-9]", "", pos), formationString, n
            )  # Place player in position
            d = AllocatePlayers(
                d, matchPlayer, rpp, d[pos][1] + 1, formation
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
