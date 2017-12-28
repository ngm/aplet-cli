""" Parsers for FeatureIDE feature model files.
"""

import xml.etree.ElementTree as et

from anytree import Node, RenderTree

from aplet.pltools.plenums import NodeType


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


class FeatureModelParser:
    """ Parses a FeatureIDE XML file and returns feature model data structure.
    """

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
