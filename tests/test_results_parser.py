import pytest

from anytree import Node, RenderTree

from aplet.pltools.parsers import TestResultsParser


# single product

# no results file 
def test_single_product_no_results_file():
    pass

def test_single_product_one_test():
    # test results parser
    parser = TestResultsParser()
    xml = """<?xml version="1.0" encoding="UTF-8"?>
<testsuites>
  <testsuite name="acceptance" tests="1" assertions="1" errors="0" failures="0" skipped="0" time="0.305924">
    <testcase file="/some/path/AddTodo.feature" name="Add todo to list: Add one-word todo" feature="Add one-word todo" assertions="1" time="0.181719"/>
  </testsuite>
</testsuites>
    """

    # act
    results = parser.get_gherkin_piece_test_statuses_for_product(xml)

    # assertions
    assert len(results) == 1
    assert results["Add one-word todo"] is True


def test_all_products():
    pass
