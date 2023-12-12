import re
import time
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
    headers = {"User-Agent": "Mozilla/5.0"}
    url = "https://www.futbin.com/players?page={}".format(pageno)
    http = ul.PoolManager()
    request = http.request("GET", url, headers=headers)
    data = unidecode(request.data.decode("utf-8"))

    alt_pos = re.findall('font-size: 12px;">[A-Z,]*<', data)
    alt_pos = [re.findall(r"(?<=>)[A-Z,]*", i)[0].split(",") for i in alt_pos]

    df = pd.DataFrame(alt_pos)
    if pageno == 1:
        df.to_csv("test.csv", index=False, header=False)
    else:
        df.to_csv("test.csv", mode="a", index=False, header=False)


if __name__ == "__main__":
    main()
