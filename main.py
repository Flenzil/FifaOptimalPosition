import pandas as pd
import grab
import optimise

FORMATIONS = pd.read_csv("../formations.csv")


def main():
    df_players = pd.read_csv("../players.csv")

    player_name = df_players["Players"]
    player_rating = df_players["Player Ratings"]
    player_type = df_players["Player Type"]

    players = grab.LoadPlayers(player_name, player_type, player_rating)

    # Restrict the formations considered to just those that the input players fit.

    allowed_formations = optimise.restrict_formations(players)
    print(allowed_formations)

    teams = []
    average_rpp = []

    teams, average_rpp = zip(
        *[
            optimise.OptimisePositions(players, FORMATIONS[i])
            for i in FORMATIONS
            if i in allowed_formations
        ]
    )
    # optimise.OptimisePositions(players, FORMATIONS["433(2)"])

    optimal_formation = teams[average_rpp.index(max(average_rpp))]
    print(teams)

    print()
    print("===========Optimal Formation:", optimal_formation.formation, "============")
    print()
    print(optimal_formation)


if __name__ == "__main__":
    main()
