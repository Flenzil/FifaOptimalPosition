import pandas as pd
import time
import random
import re
import urllib3 as ul
from unidecode import unidecode


PLAYERRATINGS = pd.read_csv("player_info.csv")
RATINGINDEX = {str(i[1]): int(i[0]) for i in pd.read_csv("index.csv").values}
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

LIVECARDS = [
    "all_rttk",
    "fc_pro",
    "fc_pro_upgrade",
]


def main():
    page = 1
    print("Checking for new players...")
    while True:
        newPlayers = get_new_players(page)  # Find new players
        updatedList = add_to_player_list(newPlayers)  # Add to list

        if len(newPlayers) < 100:  # Check if next page is needed
            break
        page += 1

    updatedList = update_live_cards(updatedList)  # Update live cards
    updatedList = sort_player_list(updatedList)  # Sort list by rating
    ratings_index(updatedList)  # Index ratings

    updatedList.to_csv("player_info.csv", index=False)  # Save
    print("Up to date!")


def get_new_players(pageno):
    """
    Collects player data from the "latest" page and places it into a DataFrame.
    """
    headers = {"User-Agent": "Mozilla/5.0"}
    url = "https://www.futbin.com/latest?page={}".format(pageno)
    http = ul.PoolManager()
    request = http.request("GET", url, headers=headers)
    data = unidecode(request.data.decode("utf-8"))

    name = re.findall(r"player_name_players_table\">[A-Za-z\'\s-]+<", data)
    name = [re.findall(r">[A-Za-z\s\'-]*", i)[0][1:] for i in name]

    id = re.findall(r'data-site-id="[0-9]+\"', data)
    id = [i[14:-1] for i in id]

    rating = re.findall(r'form rating ut24 [\w\s-]*"[\s]*>[0-9]*', data)
    rating = [i[-2:] for i in rating]

    cardType = re.findall(r'form rating ut24 [\w\s-]*"[\s]*>[0-9]*', data)
    cardType = [re.findall(r"[-\w]+", i[17:])[0] for i in cardType]

    positions = re.findall(r"<td>[A-Z]+</td>", data)
    positions = [re.findall(r"[A-Z]+", i)[0] for i in positions]

    nation = re.findall("&nation.*data", data)
    nation = [re.findall(r'title="[\w\s]*', i)[0][7:] for i in nation]

    club = re.findall("&club.*data", data)
    club = [re.findall(r'title="[\w\s.\']*', i)[0][7:] for i in club]

    playerInfo = [
        {
            "ID": id[i],
            "Name": name[i],
            "Rating": rating[i],
            "Position": positions[i],
            "Nation": nation[i],
            "Club": club[i],
            "Card Type": cardType[i],
        }
        for i in range(len(id))
        if int(id[i]) not in PLAYERRATINGS["ID"].values
    ]

    """
    Now get RPP for the new players.
    """
    for i in range(len(playerInfo)):
        if playerInfo[i]["Position"] == "GK":
            continue
        time.sleep(random.uniform(0.0, 5.0))  # Prevent 403's
        rppDict = getRPP(id[i])
        playerInfo[i] = playerInfo[i] | rppDict

    df = pd.DataFrame(playerInfo)
    return df


def getRPP(id):
    """
    Gets RPP from player page and puts them into dictionary.
    """
    url = r"https://www.futbin.com/24/player/{}".format(id)

    user_agent = r"Mozilla/5.0"
    headers = {r"User-Agent": user_agent}

    http = ul.PoolManager()
    request = http.request("GET", url, headers=headers)
    pagedata = request.data.decode("utf-8")

    rppInFile = re.findall("rpp_rating.*<", pagedata)
    rppInFile = [re.findall("[0-9]+", i) for i in rppInFile]

    rppDict = {POSITIONS[i]: rppInFile[i][0] for i in range(len(rppInFile))}

    return rppDict


def add_to_player_list(dfPlayerInfo):
    df = PLAYERRATINGS
    df = pd.concat([df, dfPlayerInfo]).reset_index(drop=True)
    return df


def sort_player_list(playerList):
    """
    Sorts player list by Rating
    """
    playerList["Rating"] = playerList["Rating"].astype(int)
    playerList.sort_values(by=["Rating"], ascending=False, inplace=True)
    playerList.reset_index(drop=True, inplace=True)
    return playerList


def ratings_index(playerList):
    """Saves the index of the first instance of each rating to save time on searching."""
    index = {}
    index[2] = str(
        playerList.loc[0, "Rating"]
    )  # +2 is added to negate the offset. Python starts at 0 but the csv file starts at 2

    for i in range(1, len(playerList)):
        if playerList.loc[i - 1, "Rating"] != playerList.loc[i, "Rating"]:
            index[i + 2] = str(playerList.loc[i, "Rating"])
    index[len(playerList) + 2] = str(playerList.loc[len(playerList) - 1, "Rating"] - 1)

    dfIndex = pd.DataFrame(index, index=["Rating"]).T
    dfIndex.to_csv("index.csv")


def update_live_cards(playerList):
    for version in LIVECARDS:
        print("Checking {}...".format(version))
        page = 1
        while True:
            url = r"https://www.futbin.com/players?page={}&version={}".format(
                page, version
            )

            user_agent = r"Mozilla/5.0"
            headers = {r"User-Agent": user_agent}

            http = ul.PoolManager()
            request = http.request("GET", url, headers=headers)
            pagedata = unidecode(request.data.decode("utf-8"))

            if len(re.findall("No Results", pagedata)) != 0:
                break

            ratings = re.findall(r'form rating ut24 [\w\s-]*"[\s]*>[0-9]*', pagedata)
            ratings = [int(i[-2:]) for i in ratings]

            nations = re.findall("&nation.*data", pagedata)
            nations = [re.findall(r'title="[\w\s]*', i)[0][7:] for i in nations]

            clubs = re.findall("&club.*data", pagedata)
            clubs = [re.findall(r'title="[\w\s.\']*', i)[0][7:] for i in clubs]

            positions = [
                (i[18:-1]) for i in re.findall(r"font-weight-bold\">[A-Z]+<", pagedata)
            ]

            names = re.findall(r'"player"\s+>[A-Za-z\s\'-]*', pagedata)
            names = [re.findall(r">[A-Za-z\s\'-]*", i)[0][1:] for i in names]

            ids = re.findall('data-playerid="[0-9]*', pagedata)
            ids = [int(i[15:]) for i in ids]

            for i in range(len(names)):
                if up_to_date(
                    names[i], positions[i], nations[i], clubs[i], ratings[i], ids[i]
                ):
                    continue
                else:
                    row = PLAYERRATINGS.loc[PLAYERRATINGS["ID"] == ids[i]].index[0]

                    playerList.at[row, "Name"] = names[i]
                    playerList.at[row, "Nation"] = nations[i]
                    playerList.at[row, "Club"] = clubs[i]
                    playerList.at[row, "Position"] = positions[i]
                    playerList.at[row, "Rating"] = ratings[i]

                    if playerList.iloc[row]["Position"] != "GK":
                        rpp = getRPP(ids[i])

                        time.sleep(random.uniform(0.0, 5.0))

                        for j in POSITIONS:
                            playerList.at[row, j] = rpp[j]
            page += 1
    return playerList


def up_to_date(name, position, nation, club, rating, id):
    row = PLAYERRATINGS.loc[PLAYERRATINGS["ID"] == id]

    currentName = row["Name"].values[0]
    currentPosition = row["Position"].values[0]
    currentNation = row["Nation"].values[0]
    currentClub = row["Club"].values[0]
    currentRating = row["Rating"].values[0]
    if (
        name == currentName
        and position == currentPosition
        and nation == currentNation
        and club == currentClub
        and rating == currentRating
    ):
        return True
    else:
        return False


if __name__ == "__main__":
    main()
