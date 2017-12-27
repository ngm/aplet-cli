import hashlib
import xml.etree.ElementTree as et
from collections import namedtuple
from os import listdir, path

import graphviz as gv
from gherkin3.parser import Parser

from aplet.utilities import NodeType, TestState

GHERKIN_PARSER = Parser()
NodeProps = namedtuple("NodeProps", "fillcolor linecolor shape style")

def get_node_props(node_type=NodeType.fmfeature, node_concrete=True, node_test_state=TestState.inconclusive):
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


def find_optional_features_rec(node):
    """ Recursive function call to find the optional nodes in its children,
    and if it is optional itself.
    """
    optionals = []

    for child in list(node):
        optionals.extend(find_optional_features_rec(child))

    mandatory = node.get("mandatory")
    abstract = node.get("abstract")

    if mandatory is None or mandatory == "false":
        if abstract is None or abstract == "false":
            optionals.extend([node.get("name")])

    return optionals


# non-mandatory, concrete features
def find_optional_features(featuremodel_filepath):
    """ Find all the optional features in a feature model.
    """
    tree = et.parse(featuremodel_filepath)
    root = tree.getroot()
    features_root = list(root.find('struct'))[0]

    return find_optional_features_rec(features_root)


def get_productmap_html_rec(node, products, depth):
    """ Build the HTML table row for a feature in a product line.
    Recursively build the rows for the feature's children, too.
    """

    html = "<tr>"

    # Name of the feature.
    feature_name = node.get("name")
    html += "<th scope='row' class='text-left' style='width:200px' >"
    html += ("&nbsp;" * depth * 4) + "&rsaquo;&nbsp;" + feature_name
    html += "</th>"

    # Whether the feature is enabled for each product.
    for product_name, product in sorted(products.items()):
        if node.get("abstract") is None:
            if feature_name in product['features']:
                html += "<td class='text-center font-weight-bold text-info'>[&plus;]</td>"
            else:
                html += "<td class='text-center'>&minus;</td>"
        else:
            html += "<td class='text-center'>&nbsp;</td>"
    html += "</tr>"

    depth += 1
    for child in list(node):
        html += get_productmap_html_rec(child, products, depth)

    return html


def get_productmap_html(model_xml_filepath, products):
    """ Build the product map HTML for a given feature model and product configurations.
    """
    with open(model_xml_filepath, "r") as model_xml_file:

        doc = et.parse(model_xml_file)
        doc_root = doc.getroot()
        root_feature = list(doc_root.find('struct'))[0]

        html = "<table class='table table-sm'>"
        html += "<thead>"
        html += "<tr>"
        html += "<th scope='row' class='text-left' style='width:200px'>Features</th>"
        for product_name, product in sorted(products.items()):
            html += "<th scope='col' class='text-center' style='max-width:100px'>"
            html += product_name
            html += "</th>"
        html += "</tr>"
        html += "</thead>"
        html += "<tbody>"
        html += get_productmap_html_rec(root_feature, products, depth=0)
        html += "</tbody>"
        html += "</table>"

    return html


def get_gherkin_pieces_grouped_by_tag(features_dir):
    """ For a list of BDD feature files, discover the parts
    that are tagged (features and scenarios) and group them by the tags.
    """

    pieces_grouped_by_tag = {}
    for feature_file in listdir(features_dir):
        feature_file = open(path.join(features_dir, feature_file), "r")
        feature_parsed = GHERKIN_PARSER.parse(feature_file.read())

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


# TODO: this could do with some refactoring.
def generate_graphviz_for_node_rec(feature, parent, graph, test_results, product_features, gherkin_pieces):
    """ For a feature node, recursively add to the graphviz graph for the node and its
    children.
    """
    feature_name = feature.get("name")
    feature_is_abstract = feature.get("abstract") is not None

    has_failed_test = False
    node_is_inconclusive = False


    # if working on a specific product, skip processing for nodes not in that product's config
    if product_features and feature_name not in product_features and not feature_is_abstract:
        return has_failed_test and False

    # recursively parse the children
    for child in feature.getchildren():
        child_has_failed = generate_graphviz_for_node_rec(
            child, feature, graph, test_results, product_features, gherkin_pieces)
        has_failed_test = has_failed_test or child_has_failed

    # add gherkin nodes
    if feature_name in gherkin_pieces:
        gherkin_pieces_for_feature = gherkin_pieces[feature_name]
        with graph.subgraph(name="cluster_" + feature_name) as subgraph:
            feature_name_hash = hashlib.sha256(feature_name.encode('utf-8')).hexdigest()
            subgraph_root_name = "cluster_" + feature_name_hash
            subgraph.node(subgraph_root_name, label="", shape="none",
                          width="0", height="0", style="invis")
            graph.edge(feature_name, subgraph_root_name)
            subgraph.attr(rankdir="TB")
            previous = subgraph_root_name
            for piece_name in gherkin_pieces_for_feature:
                piece_hash = hashlib.sha256(piece_name.encode('utf-8')).hexdigest()
                node_props = get_node_props(NodeType.gherkin_piece, True, TestState.inconclusive)
                if piece_name[3:] in test_results:
                    if test_results[piece_name[3:]] is True:
                        node_props = get_node_props(NodeType.gherkin_piece, True, TestState.passed)
                    elif test_results[piece_name[3:]] is False:
                        node_props = get_node_props(NodeType.gherkin_piece, True, TestState.failed)
                        has_failed_test = True
                subgraph.node(piece_hash, piece_name, color=node_props.linecolor,
                              fillcolor=node_props.fillcolor, shape=node_props.shape)
                subgraph.edge(previous, piece_hash, style="invis", weight="0")
                previous = piece_hash
    else:
        node_is_inconclusive = True


    node_props = get_node_props(NodeType.fmfeature, True, TestState.inconclusive)
    if feature_is_abstract:
        if node_is_inconclusive:
            node_props = get_node_props(NodeType.fmfeature, False, TestState.inconclusive)
        elif has_failed_test is True:
            node_props = get_node_props(NodeType.fmfeature, False, TestState.failed)
    else:
        if has_failed_test is True:
            node_props = get_node_props(NodeType.fmfeature, True, TestState.failed)

    # add fmfeature node
    graph.node(feature_name, feature_name,
               fillcolor=node_props.fillcolor, style=node_props.style,
               shape=node_props.shape, color=node_props.linecolor)

    # add edge to parent
    if parent is not None:
        parent_name = parent.get("name")
        arrowhead = "odot"
        if feature.get("mandatory") is not None:
            arrowhead = "dot"
        graph.edge(parent_name, feature_name, arrowhead=arrowhead)

    return has_failed_test


def generate_feature_tree_diagram(model_xml_file, features_dir, reports_dir, productconfig, output_dir, output_filename):
    """ Parse through a feature model and produce a graphviz visualisation.
    """
    tags = get_gherkin_pieces_grouped_by_tag(features_dir)
    pl_test_results = get_gherkin_piece_test_statuses(reports_dir)
    product_features = parse_product_features(productconfig)

    # Parse feature model
    tree = et.parse(model_xml_file)
    root = tree.getroot()
    features_root = root.find('struct')
    graph = gv.Digraph(format="svg")

    for feature in features_root.getchildren():
        generate_graphviz_for_node_rec(feature, None, graph, pl_test_results, product_features, tags)

    graph.render(filename=path.join(output_dir, output_filename))


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
