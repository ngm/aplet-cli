from anytree import Node

from aplet.pltools.fm import NodeType, FeatureModel
from aplet.pltools.parsers import FeatureModelParser

def test_no_gherkin_pieces():
    fm = FeatureModel()
    root = Node("root", mandatory=True, abstract=True)
    Node("child", parent=root, mandatory=True, abstract=False)
    fm.root_feature = root

    gherkin_pieces = []
    fm.add_gherkin_pieces(gherkin_pieces)

    child = list(fm.root_feature.children)[0]
    assert len(child.gherkin_pieces) == 0


def test_one_gherkin_piece():
    # arrange
    fm = FeatureModel()
    root = Node("root", mandatory=True, abstract=True)
    Node("child", parent=root, mandatory=True, abstract=False)
    fm.root_feature = root

    # act
    gherkin_pieces = {
        'child' : ['Scenario for child']
    }
    fm.add_gherkin_pieces(gherkin_pieces)

    # assert
    child = list(fm.root_feature.children)[0]
    attached_gherkin_piece = child.gherkin_pieces[0]
    assert attached_gherkin_piece.name == "Scenario for child"
    assert attached_gherkin_piece.node_type == NodeType.gherkin_piece


def test_multiple_gherkin_pieces():
    # arrange
    fm = FeatureModel()
    root = Node("root", mandatory=True, abstract=True)
    Node("child", parent=root, mandatory=True, abstract=False)
    fm.root_feature = root

    # act
    gherkin_pieces = {
        'child' : ['Scenario for child', 'Another scenario for child']
    }
    fm.add_gherkin_pieces(gherkin_pieces)

    # assert
    child = list(fm.root_feature.children)[0]
    attached_gherkin_pieces = child.gherkin_pieces
    assert len(attached_gherkin_pieces) == 2
