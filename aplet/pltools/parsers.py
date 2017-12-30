""" Parsers for FeatureIDE feature model files.
"""

import xml.etree.ElementTree as et

from anytree import Node, RenderTree

from aplet.pltools.plenums import NodeType, TestState


class FeatureModel:

    def __init__(self):
        self.root_feature = None

    def add_gherkin_pieces(self, gherkin_pieces):
        self.add_gherkin_pieces_rec(self.root_feature, gherkin_pieces) 

    def add_gherkin_pieces_rec(self, feature, gherkin_pieces):
        feature.gherkin_pieces = []
        if feature.name in gherkin_pieces:
            gherkin_pieces_for_feature = gherkin_pieces[feature.name]

            for piece_name in gherkin_pieces_for_feature:
                piece_node = Node(piece_name, parent=None, node_type=NodeType.gherkin_piece)
                feature.gherkin_pieces.append(piece_node)

        for child in feature.children:
            self.add_gherkin_pieces_rec(child, gherkin_pieces)

    def calculate_test_statuses(self, test_statuses):
        self.calculate_test_statuses_rec(self.root_feature, test_statuses) 

    def calculate_test_statuses_rec(self, feature, test_statuses):
        feature.test_status = None

        # recursively parse the children
        for child in feature.children:
            child_test_status = self.calculate_test_statuses_rec(child, test_statuses)
            if child_test_status is TestState.passed:
                if feature.test_status is None or feature.test_status is TestState.passed:
                    feature.test_status = TestState.passed
            if child_test_status is TestState.inconclusive:
                if feature.test_status is None or feature.test_status is not TestState.failed:
                    feature.test_status = TestState.inconclusive
            if child_test_status is TestState.failed:
                feature.test_status = TestState.failed

        if feature.gherkin_pieces:
            for piece in feature.gherkin_pieces:
                piece.test_status = TestState.inconclusive
                if piece.name in test_statuses:
                    if test_statuses[piece.name] is True:
                        piece.test_status = TestState.passed
                        feature.test_status = TestState.passed
                    elif test_statuses[piece.name] is False:
                        piece.test_status = TestState.failed
                        feature.test_status = TestState.failed

        if feature.test_status is None:
            feature.test_status = TestState.inconclusive

        return feature.test_status


    def trim_based_on_config(self, configured_features):
        self.trim_based_on_config_rec(self.root_feature, configured_features)

    def trim_based_on_config_rec(self, feature, configured_features):
        if not feature.abstract and feature.name not in configured_features:
            feature.parent = None

        for child in feature.children:
            self.trim_based_on_config_rec(child, configured_features)


    def optional_features_rec(self, node):
        """ Recursive function call to find the optional nodes in its children,
        and if it is optional itself.
        """
        optionals = []

        if not node.abstract and not node.mandatory:
            optionals.append(node)

        for child in node.children:
            optionals.extend(self.optional_features_rec(child))

        return optionals


    # non-mandatory, concrete features
    def optional_features(self):
        """ Find all the optional features in a feature model.
        """

        return self.optional_features_rec(self.root_feature)


class FeatureModelParser:
    """ Parses a FeatureIDE XML file and returns feature model data structure.
    """

    def parse_from_file(self, filepath):
        with open(filepath, "r") as file:
            return self.parse_xml(file.read())


    def parse_xml(self, xml):
        if not xml:
            raise Exception("XML is empty")

        xml_el = et.fromstring(xml)
        struct_el = xml_el.find('struct')

        fm = FeatureModel()

        if list(struct_el):
            features_root = list(struct_el)[0]
            fm.root_feature = self.recurse_features(features_root, None)

        return fm

    def recurse_features(self, xml_feature, parent):
        feature = Node(xml_feature.get("name"), parent=parent)
        feature.node_type = NodeType.fmfeature
        feature.abstract = bool(xml_feature.get("abstract") == "true")
        feature.mandatory = bool(xml_feature.get("mandatory") == "true")

        for xml_child in list(xml_feature):
            self.recurse_features(xml_child, parent=feature)

        return feature
