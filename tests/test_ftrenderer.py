import pprint

from aplet.pltools.ftrenderer import FeatureTreeRenderer


def test_empty_feature_model():
    renderer = FeatureTreeRenderer()
    graph = renderer.build_graphviz_structure([], [], [], [])
    print(graph.source)

