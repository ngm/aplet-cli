from gherkin3.parser import Parser
import xml.etree.ElementTree as et
import graphviz as gv
from os import listdir, path, makedirs
import json
import pprint
import hashlib
import pprint

gherkin_parser = Parser()

def parse_feature(feature, parent, graph, test_results, product_features, tags):
    feature_name = feature.get("name")
    feature_is_abstract = feature.get("abstract") is not None

    has_failed_test = False
    fillcolor = "white"

    if product_features and feature_name not in product_features and not feature_is_abstract:
        return has_failed_test and False

    for child in feature.getchildren():
        child_has_failed = parse_feature(child, feature, graph, test_results, product_features, tags)
        has_failed_test = has_failed_test or child_has_failed

    # add gherkin nodes
    if feature_name in tags:
        tags_for_feature = tags[feature_name]
        with graph.subgraph(name="cluster_" + feature_name) as subgraph:
            feature_name_hash = hashlib.sha256(feature_name.encode('utf-8')).hexdigest()
            subgraph_root_name = "cluster_" + feature_name_hash
            subgraph.node(subgraph_root_name, label="", shape="none", width="0", height="0", style="invis")
            graph.edge(feature_name, subgraph_root_name)
            subgraph.attr(rankdir="TB")
            previous = subgraph_root_name
            for piece_name in tags_for_feature:
                piece_hash = hashlib.sha256(piece_name.encode('utf-8')).hexdigest()
                line_color = "#000000"
                if piece_name[3:] in test_results:
                    if test_results[piece_name[3:]] == True:
                        line_color = "#00cc00"
                    elif test_results[piece_name[3:]] == False:
                        line_color = "#ff0000"
                        has_failed_test = True
                subgraph.node(piece_hash, piece_name, color=line_color, fillcolor="white", shape="box")
                subgraph.edge(previous, piece_hash, style="invis", weight="0")
                previous = piece_hash

    # add fmfeature node
    line_color = "green"
    if feature_is_abstract:
        fillcolor = "#cccccc"
        if has_failed_test is True:
            fillcolor = "#ffcccc"
            line_color = "red"
    else:
        if has_failed_test is True:
            fillcolor = "#ffeeee"
            line_color = "red"

    graph.node(feature_name, feature_name, fillcolor=fillcolor, style='filled', shape='box', color=line_color)

    # add edge to parent
    if parent is not None:
        parent_name = parent.get("name")
        arrowhead = "odot"
        if feature.get("mandatory") is not None:
            arrowhead = "dot"
        graph.edge(parent_name, feature_name, arrowhead=arrowhead)

    return has_failed_test

def parse_tags_from_feature_files(features_dir):
    tags = {}
    for feature_file in listdir(features_dir):
        feature_file = open(path.join(features_dir, feature_file), "r")
        feature_parsed = gherkin_parser.parse(feature_file.read())

        for tag in feature_parsed['tags']:
            tag_name = tag['name'][1:] # remove @
            if tag_name not in tags:
                tags[tag_name] = []
            tags[tag_name].append("F: " + feature_parsed['name'])

        for scenario in feature_parsed['scenarioDefinitions']:
            for tag in scenario['tags']:
                tag_name = tag['name'][1:] # remove @
                if tag_name not in tags:
                    tags[tag_name] = []
                tags[tag_name].append("S: " + scenario['name'])

    return tags

# For all product reports, go through results
# If there's a failure in any product for a given feature, that's a failure for the PL.
def parse_test_results(reports_dir):
    pl_test_results = {}
    xml_files = [file for file in listdir(reports_dir) if file.endswith(".xml")]
    for test_results_file in xml_files:
        file_path = path.join(reports_dir, test_results_file)
        tree = et.parse(file_path)
        root = tree.getroot()
        acceptance_suite = root.find('testsuite')

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
    product_features = []

    if productconfig is not "all":
        if not path.exists(productconfig):
            raise IOError("File {0} does not exist".format(productconfig))
        # features = features filtered by product config
        with open(productconfig) as product_config_file:
            for config_option in product_config_file:
                product_features.append(config_option.strip())

        product_features.append("todoapp")

    return product_features


def parse_feature_model(model_xml_file, features_dir, reports_dir, productconfig, output_dir, output_filename):
    tags = parse_tags_from_feature_files(features_dir)
    pl_test_results = parse_test_results(reports_dir)
    product_features = parse_product_features(productconfig)

    # Parse feature model
    tree = et.parse(model_xml_file)
    root = tree.getroot()
    features_root = root.find('struct')
    graph = gv.Digraph(format="svg")

    for feature in features_root.getchildren():
        parse_feature(feature, None, graph, pl_test_results, product_features, tags)

    graph.render(filename=path.join(output_dir, output_filename))

if __name__ == '__main__':
    parse_feature_model()
