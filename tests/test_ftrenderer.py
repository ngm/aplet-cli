import pprint

from aplet.pltools.ftrenderer import FeatureTreeRenderer


def test_empty_feature_model():
    renderer = FeatureTreeRenderer()
    graphviz_struct = renderer.build_graphviz_graph([], [], [], [])
    print(graphviz_struct.source)

