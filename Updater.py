import pandas as pd
import time
import random
import re
import urllib3 as ul
from unidecode import unidecode


PLAYERRATINGS = pd.read_csv("player_info.csv")
RATINGINDEX = {str(i[1]): int(i[0]) for i in pd.read_csv("Index.csv").values}
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
LIVECARDS = ["ucl_live", "europa_live", "fc_pro"]


def main():
    page = 1
    while True:
        newPlayers = get_new_players(page)
        updatedList = add_to_player_list(newPlayers)
        # updatedList = update_live_cards(updatedList)

        updatedList["Rating"] = updatedList["Rating"].astype(int)
        updatedList.sort_values(by=["Rating"], ascending=False, inplace=True)
        updatedList.reset_index(drop=True, inplace=True)

        ratings_index(updatedList)

        updatedList.to_csv("player_info.csv", index=False)
        """
        The latest page has 100 entries per page, so scrolls to next page if 
        necassary.
        """
        if len(newPlayers) < 100:
            break
        page += 1
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
        print(id[i])
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
    dfIndex.to_csv("Index.csv")


r"""
def update_live_cards(playerList):
    '''
    Updates the live cards like the UCL live cards.
    '''
    for i in range(len(playerList)):
        if playerList.iloc[i]["Card Type"] not in LIVECARDS:
            continue
        else:
            url = r"https://www.futbin.com/24/player/{}".format(
                playerList.iloc[i]["ID"]
            )

            user_agent = r"Mozilla/5.0"
            headers = {r"User-Agent": user_agent}

            http = ul.PoolManager()
            request = http.request("GET", url, headers=headers)
            pagedata = request.data.decode("utf-8")

            rating = re.findall(
                r"pcdisplay-rat[\s\t]*\"[\s\t]*>[\s\t]*[0-9]+", pagedata
            )[0]
            rating = re.findall("[0-9]+", rating)[0]

            position = re.findall(r"pcdisplay-pos\"[\s\t]*>[A-Z]+", pagedata)[0]
            position = re.findall("[A-Z]+", position)[0]

            nation = re.findall(r"24/nations/.+\">.+<", pagedata)[0]
            nation = re.findall(r">.+<", nation)[0][1:-1]

            club = re.findall(r"24/clubs/.+\">.+<", pagedata)[0]
            club = re.findall(r">.+<", club)[0][1:-1]
            if (
                int(rating) == PLAYERRATINGS.loc[i]["Rating"]
                and position == PLAYERRATINGS.loc[i]["Position"]
                and nation == PLAYERRATINGS.loc[i]["Nation"]
                and club == PLAYERRATINGS.loc[i]["Club"]
            ):
                continue

            playerList.iloc[i]["Nation"] = nation
            playerList.iloc[i]["Club"] = club
            playerList.iloc[i]["Position"] = position
            playerList.iloc[i]["Rating"] = rating

            if playerList.iloc[i]["Position"] != "GK":
                rpp = getRPP(playerList.iloc[i]["ID"])

                for j in POSITIONS:
                    playerList.iloc[i][j] = rpp[j]

    return playerList
"""

if __name__ == "__main__":
    main()
