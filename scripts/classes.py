import re
import scripts.utils as utils

__all__ = ["Player", "Team"]


class Player:
    def __init__(self, name, rpp):
        self.name = name
        self.rpp = rpp

    def __repr__(self):
        return self.name

    def nth_best_pos(self, n):
        # Returns the position with the players nth highest rpp
        sorted_rpp = sorted(self.rpp, key=self.rpp.get, reverse=True)
        return sorted_rpp[n]

    def pos_rank(self, position):
        # Returns the players rank in position.
        sorted_rpp = sorted(self.rpp, key=self.rpp.get, reverse=True)
        return sorted_rpp.index(utils.remove_nums(position))


class Team:
    def __init__(self, formation):
        self.formation = formation.name
        self.positions = list(formation)
        self.players = {i: Player("", {}) for i in self.positions}
        self.ranks = {i: 0 for i in self.positions}
        self.ratings = {i: 0 for i in self.positions}

    def __repr__(self):
        for i in self.positions:
            print(i + ": " + str(self.players[i]))
        return ""

    def place_player(self, player, position):
        """
        Places player in dictionary d while accounting for any trailing numbers
        that the keys in d might have. Checks if position is already filled.
        In addition to returning the dictionary, returns a 0 to indicate successful
        placement or 1 to indicate no placement i.e all positions already occupied.
        """
        try:
            if self.players[position].name == "":
                self.players[position] = player
                self.ratings[position] = player.rpp[position]
                self.ranks[position] = player.pos_rank(position)
                return 0
            else:
                return 1

        except KeyError:
            for i in self.get_numbered_pos(position):
                if self.players[i].name == "":
                    self.players[i] = player
                    self.ratings[i] = player.rpp[utils.remove_nums(position)]
                    self.ranks[i] = player.pos_rank(position)
                    return 0

            return 1

    def replace_player(self, position, player):
        self.players[position] = player
        self.ratings[position] = player.rpp[utils.remove_nums(position)]
        self.ranks[position] = player.pos_rank(position)

    def get_player_pos(self, player_name):
        return [i for i in self.players if self.players[i].name == player_name][0]

    def get_numbered_pos(self, position):
        regex = position + "[0-9]*"
        positions = [re.findall(regex, i) for i in self.positions]

        return [i[0] for i in positions if i != []]

    def nearest_valid_pos(self, player, rank, backward=False, return_rank=False):
        """
        Returns players next or previous best positional rating that exists in the
        current formation.
        """
        p = 0
        if backward:
            p = 1

        m = rank + (-1) ** p
        pos = player.nth_best_pos(m)

        while pos not in utils.remove_nums(self.positions):
            m = m + (-1) ** p
            pos = player.nth_best_pos(m)

        if return_rank:
            return m

        return pos
