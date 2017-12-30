""" Parsers for FeatureIDE feature model files.
"""

import xml.etree.ElementTree as et

from anytree import Node, RenderTree

from aplet.pltools.fm import FeatureModel, NodeType, TestState


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
