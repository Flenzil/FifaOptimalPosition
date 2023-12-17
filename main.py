import pandas as pd
import scripts.optimise as optimise
import scripts.grab as grab

FORMATIONS = pd.read_csv("data/formations.csv")


def main():
    df_players = pd.read_csv("data/players.csv")

    player_name = df_players["Players"]
    player_rating = df_players["Player Ratings"]
    player_type = df_players["Player Type"]

    players = grab.LoadPlayers(player_name, player_type, player_rating)

    # Restrict the formations considered to just those that the input players fit.

    allowed_formations = optimise.restrict_formations(players)

    teams, average_rpp = zip(
        *[
            optimise.OptimisePositions(players, FORMATIONS[i])
            for i in FORMATIONS
            if i in allowed_formations
        ]
    )
    # optimise.OptimisePositions(players, FORMATIONS["433(2)"])

    optimal_formation = teams[average_rpp.index(max(average_rpp))]

    print()
    print(f"===========Optimal Formation: {optimal_formation.formation}============")
    print()
    print(optimal_formation)


if __name__ == "__main__":
    main()
