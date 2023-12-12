import urllib3 as ul
import time
import pandas as pd
import re
import random

LINESTART = 18138
LINEEND = 18893
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
    # test = r"18979, Pele, 95, CAM, Brazil, EA FC ICONS, icon"
    # save_rpp(test)

    dfPlayers = pd.read_csv("../player_info.csv")
    for i in range(LINESTART, LINEEND + 1):
        print(i)
        save_rpp(dfPlayers["ID"][i])
        time.sleep(random.uniform(0.0, 10.0))


def save_rpp(id):
    url = r"https://www.futbin.com/24/player/{}".format(id)

    user_agent = r"Mozilla/5.0"
    headers = {r"User-Agent": user_agent}

    http = ul.PoolManager()
    request = http.request("GET", url, headers=headers)
    pagedata = request.data.decode("utf-8")

    rpp_in_file = re.findall("rpp_rating.*<", pagedata)
    rpp_in_file = [re.findall("[0-9]+", i) for i in rpp_in_file]

    rppDict = {POSITIONS[i]: rpp_in_file[i][0] for i in range(len(rpp_in_file))}

    dfrpp = pd.DataFrame(rppDict, index=[0])
    print(id)
    if id == 18979:
        dfrpp.to_csv("rpp.csv")
    else:
        dfrpp.to_csv("rpp.csv", mode="a", header=False)


if __name__ == "__main__":
    main()
