""" Provides ProductMapRenderer for building product map in HTML.
"""
import xml.etree.ElementTree as et

class ProductMapRenderer:
    """ Build the product map HTML for a given feature model and product configurations.
    """

    def get_productmap_html(self, model_xml_filepath, products):
        """ Construct the product map HTML for the feature model and product configurations.
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
            html += self.get_productmap_html_rec(child, products, depth)

        return html
