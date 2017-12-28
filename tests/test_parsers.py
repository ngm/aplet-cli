import pytest

from anytree import Node, RenderTree

from aplet.pltools.parsers import FeatureModelParser

def test_empty_xml():
    with pytest.raises(Exception):
        parser = FeatureModelParser()
        parser.parse_xml("")


def test_empty_feature_model():
    xml = """<?xml version="1.0" encoding="UTF-8" standalone="no"?>
	<featureModel>
		<properties/>
		<struct/>
		<constraints/>
	</featureModel>
    """
    parser = FeatureModelParser()
    fm = parser.parse_xml(xml)
    assert not fm.root_feature


def test_feature_model_with_root_feature():
    xml = """<?xml version="1.0" encoding="UTF-8" standalone="no"?>
	<featureModel>
		<properties/>
		<struct>
			<and abstract="true" mandatory="true" name="productline">
            </and>
		</struct>
		<constraints/>
	</featureModel>
    """
    parser = FeatureModelParser()
    fm = parser.parse_xml(xml)
    root_feature = fm.root_feature

    assert root_feature.name == "productline"
    assert root_feature.abstract is True
    assert root_feature.mandatory is True


def test_feature_model_with_child():
    xml = """<?xml version="1.0" encoding="UTF-8" standalone="no"?>
	<featureModel>
		<properties/>
		<struct>
			<and abstract="true" mandatory="true" name="productline">
                <feature mandatory="true" name="mandatory_child"/>
            </and>
		</struct>
		<constraints/>
	</featureModel>
    """
    parser = FeatureModelParser()
    fm = parser.parse_xml(xml)
    root_feature = fm.root_feature

    child = list(root_feature.children)[0]

    assert child.name == "mandatory_child"


def test_feature_model_with_nested_children():
    xml = """<?xml version="1.0" encoding="UTF-8" standalone="no"?>
	<featureModel>
		<properties/>
		<struct>
			<and abstract="true" mandatory="true" name="productline">
                <and abstract="true" mandatory="true" name="mandatory_child">
                    <feature mandatory="true" name="mandatory_grandchild"/>
                </and>
            </and>
		</struct>
		<constraints/>
	</featureModel>
    """
    parser = FeatureModelParser()
    fm = parser.parse_xml(xml)
    root_feature = fm.root_feature

    child = list(root_feature.children)[0]
    grandchild = list(child.children)[0]

    assert grandchild.name == "mandatory_grandchild"
