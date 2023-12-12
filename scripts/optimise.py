import pandas as pd
import scripts.classes as classes
import scripts.utils as utils

FORMATIONS = pd.read_csv("data/formations.csv")

__all__ = ["OptimisePositions"]


def OptimisePositions(players, formation):
    """
    Returns a dictionary containing the formation and where each player should
    optimally play in that formation, maximising RPP. Also returns average RPP
    for this formation.
    """
    team = classes.Team(formation)

    for player in players:
        AllocatePlayers(team, player, 0)

    # Average rpp for formation
    print(team)
    avg = 0
    for pos, player in team.players.items():
        avg += player.rpp[utils.remove_nums(pos)]

    avg /= len(team.positions)
    return team, avg


def AllocatePlayers(team, player, rank, force=False):
    """
    Fills a dictionary of positions : [players, n] such that the players are
    in their nth highest rpp. Attempts to place a  player in their best position
    unless there is another player better than them in that position.
    In that case, they are placed in their next best position until all
    players are placed.
    If force = True, the player cannot lose any position_in_teamups. This is used to resolve
    unresolvable collisions, where both players are in their loweest rated position.
    One of the players is then put back through this function with force = True.
    """
    pos = player.nth_best_pos(rank)

    print(player, pos)
    print(team.positions)
    if pos not in utils.remove_nums(team.positions):
        rank = team.nearest_valid_pos(player, rank, return_rank=True)
        pos = player.nth_best_pos(rank)

    print(player, pos)
    print(team)
    print(team.ranks)
    if team.place_player(player, pos) == 0:
        return

    if len(player.rpp) == 1:
        replace_lowest_rated_player_in_pos(team, pos, player)
        return

    # Player was not placed and there are duplicate positions that are all filled.
    player_in_team = find_best_pos_to_displace(team, pos, player, rank, force=force)

    if isinstance(player_in_team, int):
        if player_in_team == 1:
            AllocatePlayers(team, player, rank + 1, force=force)
            return
        if player_in_team == 2:
            rank = team.nearest_valid_pos(player, rank, backward=True, return_rank=True)
            AllocatePlayers(team, player, rank, force=True)
            return

    position_in_team = team.get_player_pos(player_in_team.name)

    # Moves player in current position to thier next best position and
    # places current player in current position
    rank = team.ranks[position_in_team]  # Player is in thier rankth best position.
    team.replace_player(position_in_team, player)

    # Recrusive call
    AllocatePlayers(team, player_in_team, rank + 1, force=force)
    return


def replace_lowest_rated_player_in_pos(team, pos, player):
    positions = team.get_numbered_pos(pos)

    position_in_place = positions[0]
    player_in_place = team.players[positions[0]]
    rank_in_place = team.ranks[positions[0]]
    rating_in_place = team.ratings[positions[0]]

    for i in positions:
        if team.ratings[i] < rating_in_place:
            position_in_place = positions[i]

    team.replace_player(position_in_place, player)
    AllocatePlayers(team, player_in_place, rank_in_place + 1)

    return position_in_place


def find_best_pos_to_displace(team, pos, player, rank, force=False):
    """
    Formations can have multiples of the same position, i.e CM1, CM2. We find
    these repeat formations and proceed with the position that results
    in the biggest increase to average rpp when swapped with the current
    player.
    """
    positions_in_team = team.get_numbered_pos(pos)

    players_in_team = []
    for i in positions_in_team:
        if team.ranks[i] < len(team.players[i].rpp):
            players_in_team.append(team.players[i])

    if len(players_in_team) == 0:
        return 1

    r_player, r_player_next = rating_and_next(team, player, pos, rank)
    if force:
        r_player = 1000
        force = False

    diff = []
    for i in range(len(positions_in_team)):
        r_player_in_position, r_player_in_position_next = rating_and_next(
            team,
            players_in_team[i],
            positions_in_team[i],
            team.ranks[positions_in_team[i]],
        )

        if r_player_next == -1000 and r_player_in_position_next == -1000:
            if i == len(positions_in_team) - 1:
                return 2
            else:
                continue

        avg1 = (r_player_in_position + r_player_next) / 2
        avg2 = (r_player_in_position_next + r_player) / 2

        diff.append(avg1 - avg2)

    if min(diff) > 0:
        return 1

    return players_in_team[diff.index(min(diff))]


def rating_and_next(team, player, position, rank):
    """
    Returns rating of player in position and their rating in their next best
    rating. If no valid next best rating is found, retun a very low number so
    it will always lose matchups.
    """
    rating = player.rpp[utils.remove_nums(position)]
    try:
        next_best_rating = player.rpp[team.nearest_valid_pos(player, rank)]
    except IndexError:
        next_best_rating = -1000
    print(position, rating)
    print(next_best_rating)
    return rating, next_best_rating


class FPlayer(classes.Player):
    def __init__(self, name, rpp):
        super().__init__(name, rpp)
        self.history = []
        self.placed = False


class FTeam(classes.Team):
    def __init__(self, formation):
        super().__init__(formation)
        self.players = {i: FPlayer("", {}) for i in self.positions}

    def fill_position(self, position, players):
        """
        Places player in position. If no player fits in position, then check already
        placed players to see if any of those could move to that position.
        """
        positionNoNums = utils.remove_nums(position)

        for player in players:
            historyNoNums = utils.remove_nums(player.history)
            if positionNoNums in player.rpp and positionNoNums not in historyNoNums:
                # Place player in position
                self.players[position] = player

                # If player has been moved from a previous position, empty that position
                # otherwise, remove player from list of unplaced players.
                if len(player.history) > 0:
                    self.players[player.history[-1]].name = ""
                else:
                    player.placed = True

                # Add position to player history so they won't be placed there again.
                player.history.append(position)
                return True

        # If no player fits the position, check the already placed players that haven't already
        # been in that position at some point in their history.
        placedPlayers = []
        for player_in_team in self.players.values():
            if player_in_team.name == "":
                continue
            historyNoNums = utils.remove_nums(player_in_team.history)
            for player_positions in player_in_team.rpp:
                if (
                    positionNoNums in player_positions
                    and positionNoNums not in historyNoNums
                ):
                    placedPlayers.append(player_in_team)

        # If no placed player matches either, then return False
        if placedPlayers == []:
            return False
        #
        # Recursive call to place player from list of eligible placed players.
        return self.fill_position(position, placedPlayers)


def restrict_formations(players):
    """
    Restricts formations to only those that can support the inputted players
    Attemps to fill each formation with the input players. If a position cannot
    be filled by any player then the formation is invalid.
    """
    invalidFormations = []

    for formationName, formation in FORMATIONS.items():
        # Dictionary to contain filled positions.
        team = FTeam(formation)

        # Create an array of objects, f_players (formation players) which inherit
        # from players but adds a history parameter to track which positions a
        # player has already been placed in.
        f_players = []
        for player in players:
            f_players.append(FPlayer(player.name, player.rpp))

        i = 0
        while True:
            # As long as there is an empty position in the team, keep looping through
            # players.
            position = formation[i % len(formation)]

            if team.players[position].name == "":
                if not team.fill_position(position, f_players):
                    invalidFormations.append(formationName)
                    break

            for j in f_players:
                if j.placed:
                    f_players.remove(j)

            # Team successfully filled
            if all([j.name != "" for j in team.players.values()]):
                break
            i += 1

    allowedFormations = [i for i in FORMATIONS if i not in invalidFormations]

    if allowedFormations == []:
        raise SystemExit("Not a valid team!")

    return allowedFormations


if __name__ == "__main__":
    import pandas as pd
    import grab

    dfplayers = pd.read_csv("../players.csv")

    playerName = dfplayers["Players"]
    playerRating = dfplayers["Player Ratings"]
    playerType = dfplayers["Player Type"]

    players = grab.LoadPlayers(playerName, playerType, playerRating)
    allowed_formations = restrict_formations(players)
    print(allowed_formations)
    # OptimisePositions(players, FORMATIONS["433"])
