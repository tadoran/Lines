from enum import Enum


class GameStatus(Enum):
    RUNNING = 0
    LOST = 1
    WON = 2


class CoordinatesMoves(Enum):
    LEFT = (0, -1)
    RIGHT = (0, 1)
    UP = (-1, 0)
    DOWN = (1, 0)
    UP_LEFT = (-1, -1)
    UP_RIGHT = (-1, 1)
    DOWN_LEFT = (1, -1)
    DOWN_RIGHT = (1, 1)


class GameDifficulty(Enum):
    EASY = (10, 10)
    MEDIUM = (12, 12)
    HARD = (15, 15)
