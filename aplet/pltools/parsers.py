""" Parsers for FeatureIDE feature model files.
"""

import xml.etree.ElementTree as et
from os import listdir, path

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



class ProductConfigParser:

    def __init__(self, root_feature_name):
        self.root_feature_name = root_feature_name

    def parse_config(self, productconfig):
        """ For a given product configuration file, pull out the list of features
        it has been configured to have.
        """
        product_features = []

        if not path.exists(productconfig):
            raise IOError("File {0} does not exist".format(productconfig))
        # features = features filtered by product config
        with open(productconfig) as product_config_file:
            for config_option in product_config_file.readlines():
                product_features.append(config_option.strip())

        # TODO: shouldn't be hardcoding the appending of this.
        product_features.append(self.root_feature_name)

        return product_features



class TestResultsParser:

    def get_gherkin_piece_test_statuses_for_product_from_file(self, xmlresults_path):
        if not path.exists(xmlresults_path):
            return {}

        with open(xmlresults_path, "r") as file:
            xml = file.read()
            return self.get_gherkin_piece_test_statuses_for_product(xml)


    def get_gherkin_piece_test_statuses_for_product(self, testresultsxml):
        tree = et.fromstring(testresultsxml)
        acceptance_suite = tree.find('testsuite')

        results = {}

        if acceptance_suite is not None:
            for testcase in acceptance_suite:
                scenario_name = testcase.get("feature")
                passed = True
                if testcase.find("failure") is not None:
                    passed = False
                results[scenario_name] = passed

        return results


    def get_gherkin_piece_test_statuses_for_dir(self, reports_dir):
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
            results_for_product = self.get_gherkin_piece_test_statuses_for_product_from_file(file_path)

            for scenario_name in results_for_product:
                if scenario_name not in pl_test_results:
                    pl_test_results[scenario_name] = True

                result_for_product = results_for_product[scenario_name]
                pl_test_results[scenario_name] = pl_test_results[scenario_name] and result_for_product

        return pl_test_results
