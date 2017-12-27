from enum import Enum

class NodeType(Enum):
    """ Simple enum for node types. """
    fmfeature = 1
    gherkin_piece = 2

class TestState(Enum):
    """ Simple enum for test states. """
    inconclusive = 1
    failed = 2
    passed = 3
