import pandas as pd
import time
import random
import re
import urllib3 as ul
from unidecode import unidecode


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
        updatedList = update_live_cards(updatedList)

        updatedList["Rating"] = updatedList["Rating"].astype(int)
        updatedList.sort_values(by=["Rating"], inplace=True)
        ratings_index(updatedList)

        updatedList.to_csv("test.csv")
        if len(newPlayers) < 100:
            break
        page += 1


def get_new_players(pageno):
    # player_info = {'name' : , 'id' : , 'rating' : , 'position' : , 'type' : }

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

    card = re.findall(r'form rating ut24 [\w\s-]*"[\s]*>[0-9]*', data)

    cardType = [re.findall(r"[-\w]+", i[17:])[0] for i in card]

    positions = re.findall(r"<td>[A-Z]+</td>", data)
    positions = [re.findall(r"[A-Z]+", i)[0] for i in positions]

    nation = re.findall("&nation.*data", data)
    nation = [re.findall(r'title="[\w\s]*', i)[0][7:] for i in nation]

    club = re.findall("&club.*data", data)
    club = [re.findall(r'title="[\w\s.\']*', i)[0][7:] for i in club]

    playerList = pd.read_csv("test.csv")

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
        if int(id[i]) not in playerList["ID"].values
    ]

    for i in range(len(playerInfo)):
        if playerInfo[i]["Position"] == "GK":
            continue
        time.sleep(random.uniform(0.0, 10.0))
        print(id[i])
        rppDict = getRPP(id[i])
        playerInfo[i] = playerInfo[i] | rppDict

    df = pd.DataFrame(playerInfo)
    print(df)
    return df


def getRPP(id):
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
    df = pd.read_csv("test.csv")
    """
    for i in range(len(dfPlayerInfo)):
        ratingIndex = {
            str(i[1]): int(i[0]) for i in pd.read_csv("Index_test.csv").values
        }
        index = ratingIndex[str(dfPlayerInfo.iloc[i]["Rating"])]
        df = pd.concat([df[:index], dfPlayerInfo.iloc[[i]], df[index:]]).reset_index(
            drop=True
        )
        ratings_index(df)
    """
    df = pd.concat([df, dfPlayerInfo]).reset_index(drop=True)

    df.to_csv("test.csv", index=False)


def ratings_index(playerList):
    print(playerList)
    print(str(playerList.loc[0, "Rating"]))
    index = {}
    index[0] = str(playerList.loc[0, "Rating"])
    for i in range(1, len(playerList)):
        if playerList.loc[i - 1, "Rating"] != playerList.loc[i, "Rating"]:
            index[i] = str(playerList.loc[i, "Rating"])

    dfIndex = pd.DataFrame(index, index=["Rating"]).T
    dfIndex.to_csv("Index_test.csv")


def update_live_cards(playerList):
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

            rating = re.findall(r"pcdisplay-rat\">[0-9]+", pagedata)[0]
            rating = re.findall("[0-9]+", rating)

            position = re.findall(r"pcdisplay-pos\">[A-Z]+", pagedata)[0]
            position = re.findall("[A-Z]+", position)

            nation = re.findall(r"24/nations/.+\">.+<", pagedata)[0]
            nation = re.findall(r">.+<", nation)[0][1:-1]

            club = re.findall(r"24/clubs/.+\">.+<", pagedata)[0]
            club = re.findall(r">.+<", club)[0][1:]

            playerList.iloc[i]["Nation"] = nation
            playerList.iloc[i]["Club"] = club
            playerList.iloc[i]["Position"] = position
            playerList.iloc[i]["Rating"] = rating

            rpp = getRPP(playerList.iloc[i]["ID"])
            for j in POSITIONS:
                playerList.iloc[i][j] = rpp[j]

    return playerList


if __name__ == "__main__":
    main()
