import linecache
import pandas as pd
import re
from scripts.classes import Player

INDEX = pd.read_csv("data/index.csv")
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

__all__ = ["LoadPlayers", "FindPlayers"]


def LoadPlayers(playerName, playerType, playerRating):
    players = []
    for i in range(len(playerName)):
        players.append(FindPlayers(playerName[i], playerType[i], playerRating[i]))
    return players


def FindPlayers(player_name, player_type, player_rating):
    """Returns ID of player given their name, card type and rating.
    If multiple players match, user is asked to specify which one they want.
    Exits if no player is found matching the criteria."""
    matches = []
    # Find players that match
    for i in range(INDEX[player_rating], INDEX[player_rating - 1]):
        line = linecache.getline("data/player_info.csv", i)
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

    return Player(match[1], rpp)
