import re

__all__ = ["remove_nums"]


def remove_nums(positions):
    if isinstance(positions, str):
        return re.sub("[0-9]", "", positions)
    else:
        return [re.sub("[0-9]", "", i) for i in positions]
