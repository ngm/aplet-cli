""" Provides FeatureTreeRenderer for rendering a feature model with
tests to a graphviz diagram.
"""
import hashlib
import xml.etree.ElementTree as et
from collections import namedtuple
from os import path, listdir

from gherkin3.parser import Parser
import graphviz as gv

from aplet.pltools.plenums import NodeType, TestState
from aplet.pltools.parsers import FeatureModelParser

NodeProps = namedtuple("NodeProps", "fillcolor linecolor shape style")

class FeatureTreeRenderer:
    """ Generates a graphviz image for a feature model and product line test results. """

    def __init__(self):
        self.graph = gv.Digraph()


    def get_node_props(self, node_type=NodeType.fmfeature, node_concrete=True, node_test_state=TestState.inconclusive):
        """ Get a node's graphviz display properties based on it's feature model properties.
        """
        shape = None
        fillcolor = "white"
        linecolor = None
        style = "filled"

        if node_type == NodeType.fmfeature:
            shape = "box"
        elif node_type == NodeType.gherkin_piece:
            shape = "oval"

        if node_test_state == TestState.inconclusive:
            linecolor = "orange"
            if not node_concrete:
                fillcolor = "orange"
        elif node_test_state == TestState.failed:
            linecolor = "red"
            if not node_concrete:
                fillcolor = "red"
        elif node_test_state == TestState.passed:
            linecolor = "green"
            if not node_concrete:
                fillcolor = "green"

        return NodeProps(fillcolor=fillcolor, linecolor=linecolor, shape=shape, style=style)


    # TODO: this could do with some refactoring.
    def generate_graphviz_for_node_rec(self,
                                       feature, parent,
                                       test_results, product_features, gherkin_pieces):
        """ For a feature node, recursively add to the graphviz graph for the node and its
        children.
        """

        has_failed_test = False
        node_is_inconclusive = False

        # if working on a specific product, skip processing for nodes not in that product's config
        if product_features and feature.name not in product_features and not feature.abstract:
           return has_failed_test and False #TODO: this will always be false?

        # recursively parse the children
        for child in feature.children:
            child_has_failed = self.generate_graphviz_for_node_rec(
                child, feature, test_results, product_features, gherkin_pieces)
            has_failed_test = has_failed_test or child_has_failed

        # add gherkin nodes
        if feature.name in gherkin_pieces:
            gherkin_pieces_for_feature = gherkin_pieces[feature.name]
            subgraph = gv.Digraph(name="cluster_" + feature.name)
            feature_name_hash = hashlib.sha256(feature.name.encode('utf-8')).hexdigest()
            subgraph_root_name = "cluster_" + feature_name_hash
            subgraph.node(subgraph_root_name, label="", shape="none",
                          width="0", height="0", style="invis")
            self.graph.edge(feature.name, subgraph_root_name)
            subgraph.attr(rankdir="TB")
            previous = subgraph_root_name
            for piece_name in gherkin_pieces_for_feature:
                piece_hash = hashlib.sha256(piece_name.encode('utf-8')).hexdigest()
                node_props = self.get_node_props(NodeType.gherkin_piece, True, TestState.inconclusive)
                if piece_name[3:] in test_results:
                    if test_results[piece_name[3:]] is True:
                        node_props = self.get_node_props(NodeType.gherkin_piece, True, TestState.passed)
                    elif test_results[piece_name[3:]] is False:
                        node_props = self.get_node_props(NodeType.gherkin_piece, True, TestState.failed)
                        has_failed_test = True
                subgraph.node(piece_hash, piece_name, color=node_props.linecolor,
                                fillcolor=node_props.fillcolor, shape=node_props.shape)
                subgraph.edge(previous, piece_hash, style="invis", weight="0")
                previous = piece_hash
            self.graph.subgraph(subgraph)
        else:
            node_is_inconclusive = True


        node_props = self.get_node_props(NodeType.fmfeature, True, TestState.inconclusive)
        if feature.abstract:
            if node_is_inconclusive:
                node_props = self.get_node_props(NodeType.fmfeature, False, TestState.inconclusive)
            elif has_failed_test is True:
                node_props = self.get_node_props(NodeType.fmfeature, False, TestState.failed)
        else:
            if has_failed_test is True:
                node_props = self.get_node_props(NodeType.fmfeature, True, TestState.failed)

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

        return has_failed_test


    def build_graphviz_graph(self, root_feature, gherkin_pieces,
                                 gherkin_piece_test_statuses, product_features):
        """ Builds the graphviz structure ready for rendering.
        """
        self.graph = gv.Digraph()

        self.generate_graphviz_for_node_rec(root_feature, None, gherkin_piece_test_statuses,
                                            product_features, gherkin_pieces)

        return self.graph


    def generate_feature_tree_diagram(self,
                                      model_xml_file, features_dir, reports_dir, productconfig):
        """ Parse through a feature model and test results and produce a graphviz visualisation.
        """
        gherkin_pieces = gherkin_pieces_grouped_by_tag(features_dir)
        gherkin_piece_test_statuses = get_gherkin_piece_test_statuses(reports_dir)
        product_features = parse_product_features(productconfig)

        feature_model = None
        with open(model_xml_file, "r") as xml_file:
            fmparser = FeatureModelParser()
            feature_model = fmparser.parse_xml(xml_file.read())

        self.build_graphviz_graph(feature_model.root_feature, gherkin_pieces,
                                      gherkin_piece_test_statuses, product_features)


    def render_as_svg(self, output_dir, output_filename):
        """ Render the built graph as an svg
        """
        self.graph.format = "svg"
        self.graph.render(filename=path.join(output_dir, output_filename))


def get_gherkin_piece_test_statuses(reports_dir):
    """ For previously produced test reports for all products in the product
    line, parse through the results. For each scenario that has been run for
    all of the products, check whether it passed or failed.
    If there's a failure in any product for a given gherkin piece for any product
    that counts as a failure for that gherkin piece for the whole product line.
    # TODO: not sure exactly how this is working.
    # TODO: should this be including inconclusive status?
    """

    pl_test_results = {}
    xml_files = [file for file in listdir(reports_dir) if file.endswith(".xml")]
    for test_results_file in xml_files:
        file_path = path.join(reports_dir, test_results_file)
        tree = et.parse(file_path)
        root = tree.getroot()
        acceptance_suite = root.find('testsuite')

        if acceptance_suite is not None:
            for testcase in acceptance_suite:
                scenario_name = testcase.get("feature")
                passed = True
                if testcase.find("failure") is not None:
                    passed = False
                if scenario_name not in pl_test_results:
                    pl_test_results[scenario_name] = True
                pl_test_results[scenario_name] = pl_test_results[scenario_name] and passed

    return pl_test_results


def product_test_status(reports_dir, productname):
    """ Determine the test status for a given product, based on its test report.
    If there's a failure for any feature, that's a failure for the entire product.
    """

    file_path = path.join(reports_dir, "report" + productname + ".xml")
    tree = et.parse(file_path)
    root = tree.getroot()
    acceptance_suite = root.find('testsuite')

    test_state = TestState.inconclusive
    for testcase in acceptance_suite:
        test_state = TestState.passed
        if testcase.find("failure") is not None:
            test_state = TestState.failed
            break

    return test_state


def gherkin_pieces_grouped_by_tag(features_dir):
    """ For a list of BDD feature files, discover the parts
    that are tagged (features and scenarios) and group them by the tags.
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
            pieces_grouped_by_tag[tag_name].append("F: " + feature_parsed['name'])

        for scenario in feature_parsed['scenarioDefinitions']:
            for tag in scenario['tags']:
                tag_name = tag['name'][1:] # remove @
                if tag_name not in pieces_grouped_by_tag:
                    pieces_grouped_by_tag[tag_name] = []
                pieces_grouped_by_tag[tag_name].append("S: " + scenario['name'])

    return pieces_grouped_by_tag


def parse_product_features(productconfig):
    """ For a given product configuration file, pull out the list of features
    it has been configured to have.
    """
    product_features = []

    # TODO: if it's all we just return an empty list?
    if productconfig != "all":
        if not path.exists(productconfig):
            raise IOError("File {0} does not exist".format(productconfig))
        # features = features filtered by product config
        with open(productconfig) as product_config_file:
            for config_option in product_config_file:
                product_features.append(config_option.strip())

        # TODO: shouldn't be hardcoding the appending of this.
        product_features.append("todoapp")

    return product_features
