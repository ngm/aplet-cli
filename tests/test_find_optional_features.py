from anytree import Node

from aplet.pltools.plenums import NodeType, TestState
from aplet.pltools.parsers import FeatureModel


def test_no_optional_features():
    # arrange
    fm = FeatureModel()
    root = Node("root", mandatory=True, abstract=True)
    Node("child", parent=root, mandatory=True, abstract=False)
    fm.root_feature = root

    # act
    optional_features = fm.optional_features()

    # assert
    assert not optional_features


def test_one_optional_features():
    # arrange
    fm = FeatureModel()
    root = Node("root", mandatory=True, abstract=True)
    Node("child", parent=root, mandatory=False, abstract=False)
    fm.root_feature = root

    # act
    optional_features = fm.optional_features()

    # assert
    assert len(optional_features) == 1
    assert optional_features[0].name == "child"


def test_multiple_optional_features():
    # arrange
    fm = FeatureModel()
    root = Node("root", mandatory=True, abstract=True)
    child = Node("child", parent=root, mandatory=False, abstract=False)
    Node("grandchild", parent=child, mandatory=False, abstract=False)
    fm.root_feature = root

    # act
    optional_features = fm.optional_features()

    # assert
    assert len(optional_features) == 2
    assert optional_features[0].name == "child"
    assert optional_features[1].name == "grandchild"


def test_abstract_optional_features_ignored():
    # arrange
    fm = FeatureModel()
    root = Node("root", mandatory=True, abstract=True)
    child = Node("child", parent=root, mandatory=False, abstract=True)
    Node("grandchild", parent=child, mandatory=False, abstract=False)
    fm.root_feature = root

    # act
    optional_features = fm.optional_features()

    # assert
    assert len(optional_features) == 1
    assert optional_features[0].name == "grandchild"
