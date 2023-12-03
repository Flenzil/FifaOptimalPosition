import time
import re
import random
from unidecode import unidecode
import pandas as pd
import urllib3 as ul

PAGESTART = 1
PAGEEND = 634


def main():
    for i in range(PAGESTART, PAGEEND + 1):
        # r = random.randint(1, 2)
        get_player_ids(i)
        print(i)
        time.sleep(random.uniform(0.0, 10.0))


def get_player_ids(pageno):
    # player_info = {'name' : , 'id' : , 'rating' : , 'position' : , 'type' : }

    headers = {"User-Agent": "Mozilla/5.0"}
    url = "https://www.futbin.com/players?page={}".format(pageno)
    http = ul.PoolManager()
    request = http.request("GET", url, headers=headers)
    data = unidecode(request.data.decode("utf-8"))

    name = re.findall(r'"player"\s+>[A-Za-z\s\'-]*', data)
    name = [re.findall(r">[A-Za-z\s\'-]*", i)[0][1:] for i in name]

    id = re.findall('data-playerid="[0-9]*', data)
    id = [i[15:] for i in id]

    rating = re.findall(r'form rating ut24 [\w\s-]*"[\s]*>[0-9]*', data)
    rating = [i[-2:] for i in rating]

    card = re.findall(r'form rating ut24 [\w\s-]*"[\s]*>[0-9]*', data)

    card_type = [
        re.findall(r"([A-Za-z-]+\s+[\w.-]+)+", i[17:])[0]
        if i[17] == " "
        else re.findall(r"(?:(?!\sgold|\ssilver|\sbronze).)+", i)[0][17:]
        for i in card
    ]

    positions = [(i[18:-1]) for i in re.findall(r"font-weight-bold\">[A-Z]+<", data)]

    nation = re.findall("&nation.*data", data)
    nation = [re.findall(r'title="[\w\s]*', i)[0][7:] for i in nation]

    club = re.findall("&club.*data", data)
    club = [re.findall(r'title="[\w\s.\']*', i)[0][7:] for i in club]

    alt_pos = re.findall('font-size: 12px;">[A-Z,]*<', data)
    alt_pos = [re.findall(r"(?<=>)[A-Z,]*", i)[0].split(",") for i in alt_pos]

    player_info = {
        id[i]: {
            "Name": name[i],
            "Rating": rating[i],
            "Position": positions[i],
            "Nation": nation[i],
            "Club": club[i],
            "Card Type": card_type[i],
        }
        for i in range(len(id))
    }
    for i in range(len(id)):
        for j in range(3):
            try:
                player_info[id[i]]["Alt-Pos{}".format(str(j + 1))] = alt_pos[i][j]
            except IndexError:
                player_info[id[i]]["Alt-Pos{}".format(str(j + 1))] = ""

    df = pd.DataFrame(player_info).T
    df = df[
        [
            "Name",
            "Rating",
            "Position",
            "Alt-Pos1",
            "Alt-Pos2",
            "Alt-Pos3",
            "Nation",
            "Club",
            "Card Type",
        ]
    ]
    if pageno == 1:
        df.to_csv("player_info2.csv")
    else:
        df.to_csv("player_info2.csv", mode="a", header=False)


if __name__ == "__main__":
    main()
