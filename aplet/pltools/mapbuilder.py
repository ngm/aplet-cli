""" Provides ProductMapRenderer for building product map in HTML.
"""
import xml.etree.ElementTree as et

from aplet.pltools.fm import TestState

class ProductMapRenderer:
    """ Build the product map HTML for a given feature model and product configurations.
    """

    def get_productmap_html(self, feature_model, products):
        """ Construct the product map HTML for the feature model and product configurations.
        """
        root_feature = feature_model.root_feature

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
        html += self.get_productmap_html_rec(root_feature, products, depth=0)
        html += "</tbody>"
        html += "</table>"

        return html


    def get_productmap_html_rec(self, node, products, depth):
        """ Build the HTML table row for a feature in a product line.
        Recursively build the rows for the feature's children, too.
        """

        html = "<tr>"

        # Name of the feature.
        html += "<th scope='row' class='text-left' style='width:200px' >"
        html += ("&nbsp;" * depth * 4) + "&rsaquo;&nbsp;" + node.name
        html += "</th>"

        # Whether the feature is enabled for each product.
        for product_name, product in sorted(products.items()):
            symbol = ""
            css_classes = ["text-center"]
            if not node.abstract:
                if node.name in product['features']:
                    symbol = "[&plus;]"
                    css_classes.append("font-weight-bold")
                    if node.test_status is TestState.failed:
                        css_classes.append("text-danger")
                    elif node.test_status is TestState.passed:
                        css_classes.append("text-success")
                    else:
                        css_classes.append("text-warning")
                else:
                    symbol = "&minus;"
            else:
                symbol = "&nbsp;"
            html += "<td class='{0}'>{1}</td>".format(" ".join(css_classes), symbol)
        html += "</tr>"

        depth += 1
        for child in node.children:
            html += self.get_productmap_html_rec(child, products, depth)

        return html
