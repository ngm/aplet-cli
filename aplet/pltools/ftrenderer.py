""" Provides FeatureTreeRenderer for rendering a feature model with
tests to a graphviz diagram.
"""
import hashlib
import xml.etree.ElementTree as et
from collections import namedtuple
from os import path, listdir

from gherkin3.parser import Parser
import graphviz as gv

from aplet.pltools.fm import NodeType, TestState

NodeProps = namedtuple("NodeProps", "fillcolor linecolor shape style")

class FeatureTreeRenderer:
    """ Generates a graphviz image for a feature model and product line test results. """

    def __init__(self):
        self.graph = gv.Digraph()


    def get_node_props(self, node_type=NodeType.fmfeature, node_abstract=True, node_test_state=TestState.inconclusive):
        """ Get a node's graphviz display properties based on it's feature model properties.
        """
        shape = None
        fillcolor = "white"
        linecolor = None
        style = "filled"

        if node_type == NodeType.fmfeature:
            shape = "box"
        elif node_type == NodeType.gherkin_piece:
            shape = "box"

        if node_test_state == TestState.inconclusive:
            linecolor = "#ffa500" # orange
            if node_abstract:
                fillcolor = "#ffd72f"
        elif node_test_state == TestState.failed:
            linecolor = "red"
            if node_abstract:
                fillcolor = "#ffcccc"
        elif node_test_state == TestState.passed:
            linecolor = "green"
            if node_abstract:
                fillcolor = "#ccffcc"

        return NodeProps(fillcolor=fillcolor, linecolor=linecolor, shape=shape, style=style)


    # TODO: this could do with some refactoring.
    def generate_graphviz_for_node_rec(self, feature, parent):
        """ For a feature node, recursively add to the graphviz graph for the node and its
        children.
        """

        # recursively parse the children
        for child in feature.children:
            self.generate_graphviz_for_node_rec(child, feature)

        # add gherkin nodes
        if feature.gherkin_pieces:
            label = "<<table border='0'>"
            for piece in feature.gherkin_pieces:
                bgcolor = ""
                if piece.test_status is TestState.passed:
                    bgcolor = "#ccffcc"
                elif piece.test_status is TestState.failed:
                    bgcolor = "#ffcccc"
                elif piece.test_status is TestState.inconclusive:
                    bgcolor = "#ffd72f"

                label += "<tr>"
                label += "<td bgcolor='{0}' border='1' style='rounded'>{1}</td>".format(bgcolor, piece.name)
                label += "</tr>"
            label += "</table>>"
            self.graph.node(feature.name+"_gherkin", label=label, shape="rect")
            self.graph.edge(feature.name, feature.name+"_gherkin")

        node_props = self.get_node_props(NodeType.fmfeature, feature.abstract, feature.test_status)

        # add fmfeature node
        self.graph.node(feature.name, feature.name,
                fillcolor=node_props.fillcolor, style=node_props.style,
                shape=node_props.shape, color=node_props.linecolor)

        # add edge to parent
        if parent is not None:
            arrowhead = "odot"
            if feature.mandatory:
                arrowhead = "dot"
            self.graph.edge(parent.name, feature.name, arrowhead=arrowhead)


    def build_graphviz_graph(self, root_feature):
        """ Builds the graphviz structure ready for rendering.
        """
        self.graph = gv.Digraph()

        self.generate_graphviz_for_node_rec(root_feature, None)

        return self.graph




    def render_as_svg(self, output_dir, output_filename):
        """ Render the built graph as an svg
        """
        self.graph.format = "svg"
        self.graph.render(filename=path.join(output_dir, output_filename))


def gherkin_pieces_grouped_by_featurename(features_dir):
    """ For a list of BDD feature files, discover the parts
    that are tagged with FM feature names (features and scenarios) and group them by the FM feature names.
    """

    gherkin_parser = Parser()

    pieces_grouped_by_tag = {}
    for feature_file in listdir(features_dir):
        feature_file = open(path.join(features_dir, feature_file), "r")
        feature_parsed = gherkin_parser.parse(feature_file.read())

        for tag in feature_parsed['tags']:
            tag_name = tag['name'][1:] # remove @
            if tag_name not in pieces_grouped_by_tag:
                pieces_grouped_by_tag[tag_name] = []
            pieces_grouped_by_tag[tag_name].append(feature_parsed['name'])

        for scenario in feature_parsed['scenarioDefinitions']:
            for tag in scenario['tags']:
                tag_name = tag['name'][1:] # remove @
                if tag_name not in pieces_grouped_by_tag:
                    pieces_grouped_by_tag[tag_name] = []
                pieces_grouped_by_tag[tag_name].append(scenario['name'])

    return pieces_grouped_by_tag
