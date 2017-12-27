import xml.etree.ElementTree as et


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
