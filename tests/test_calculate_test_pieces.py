from anytree import Node

from aplet.pltools.fm import FeatureModel, NodeType, TestState

def test_one_failed_scenario():
    # arrange
    fm = FeatureModel()
    root = Node("root", mandatory=True, abstract=True)
    Node("child", parent=root, mandatory=True, abstract=False)
    fm.root_feature = root
    gherkin_pieces = {
        'child' : ['Scenario for child', 'Another scenario for child']
    }
    fm.add_gherkin_pieces(gherkin_pieces)

    # act
    test_statuses = {
        'Scenario for child' : True,
        'Another scenario for child' : False
    }
    fm.calculate_test_statuses(test_statuses)

    # assert
    assert fm.root_feature.test_status == TestState.failed


def test_all_scenarios_passed():
    # arrange
    fm = FeatureModel()
    root = Node("root", mandatory=True, abstract=True)
    Node("child", parent=root, mandatory=True, abstract=False)
    fm.root_feature = root
    gherkin_pieces = {
        'child' : ['Scenario for child', 'Another scenario for child']
    }
    fm.add_gherkin_pieces(gherkin_pieces)

    # act
    test_statuses = {
        'Scenario for child' : True,
        'Another scenario for child' : True
    }
    fm.calculate_test_statuses(test_statuses)

    # assert
    assert fm.root_feature.test_status == TestState.passed


def test_no_test_statuses():
    # arrange
    fm = FeatureModel()
    root = Node("root", mandatory=True, abstract=True)
    Node("child", parent=root, mandatory=True, abstract=False)
    fm.root_feature = root
    gherkin_pieces = {
        'child' : ['Scenario for child', 'Another scenario for child', '3rd scenario']
    }
    fm.add_gherkin_pieces(gherkin_pieces)

    # act
    test_statuses = {}
    fm.calculate_test_statuses(test_statuses)

    # assert
    assert fm.root_feature.test_status == TestState.inconclusive
