from enum import Enum


class EventType(Enum):
    KEYBOARD = "keyboard"
    MOUSE = "mouse"
    SCROLL = "scroll"
    ALL = "all"


class FeatureType(Enum):
    BROWSER = 1
    BEHAVIORAL = 2
    COMBINED = 3
