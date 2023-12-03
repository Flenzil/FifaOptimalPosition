import re
import urllib3 as ul

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
url = r"https://www.futbin.com/24/player/20305"

user_agent = r"Mozilla/5.0"
headers = {r"User-Agent": user_agent}

http = ul.PoolManager()
request = http.request("GET", url, headers=headers)
pagedata = request.data.decode("utf-8")

altposDict = {}
for i in range(3):
    regex = '(?<=alt-pos-sub-{}">)[A-Z]+'.format(i + 1)
    try:
        altpos = re.search(regex, pagedata)
        altposDict["Alt-Pos{}".format(i + 1)] = altpos.group()
    except (IndexError, AttributeError):
        altposDict["Alt-Pos{}".format(i + 1)] = ""
print(altposDict)
dfOrder = [
    "Name",
    "Rating",
    "Position",
    "Alt-Pos1",
    "Alt-Pos2",
    "Alt-Pos3",
    "Nation",
    "Club",
    "Card Type",
] + [i for i in POSITIONS]
