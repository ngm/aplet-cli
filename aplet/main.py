import shutil
import subprocess
from http.server import HTTPServer, SimpleHTTPRequestHandler
from os import chdir, listdir, makedirs, path

import click
import pkg_resources
import yaml

from aplet import utilities
from aplet.pltools import ftrenderer, mapbuilder, plutils


CONFIG = {}


@click.group()
@click.option("--configfile", default="./aplet.yml")
def cli(configfile):
    """ Default entry point to the application.
    """
    if path.exists(configfile):
        load_config("aplet.yml")
    pass


def load_config(filename):
    """ Load config file for use later in the application.
    """
    with open(filename, "r") as stream:
        try:
            global CONFIG
            CONFIG = yaml.load(stream)
        except yaml.YAMLError as ex:
            print(ex)


@cli.command()
def showconfig():
    """ Dump the discovered config file (will be discovered in cli() method.)
    """
    print(yaml.dump(CONFIG))


@cli.command()
@click.option("--projectfolder", default=".", help="Location to output the aplet files")
def init(projectfolder):
    """ Initialises an aplet project folder, containing example product line and docs templates.
    """

    productline_dir = path.join(projectfolder, "productline")
    configs_path = path.join(productline_dir, "configs")
    bddfeatures_path = path.join(projectfolder, "bddfeatures")
    testreports_path = path.join(projectfolder, "testreports")

    if not path.exists(productline_dir):
        makedirs(productline_dir)
    model_filepath = pkg_resources.resource_filename(__name__, 'templates/model.xml')
    shutil.copyfile(model_filepath, path.join(productline_dir, "model.xml"))

    if not path.exists(configs_path):
        makedirs(configs_path)
    exampleconfig_filepath = pkg_resources.resource_filename(__name__, 'templates/ExampleProduct.config')
    shutil.copyfile(exampleconfig_filepath, path.join(configs_path, "ExampleProduct.config"))

    if not path.exists(bddfeatures_path):
        makedirs(bddfeatures_path)

    if not path.exists(testreports_path):
        makedirs(testreports_path)


    # copy template config file
    configtemplate_filepath = pkg_resources.resource_filename(__name__, 'templates/aplet.yml')
    shutil.copyfile(configtemplate_filepath, path.join(projectfolder, "aplet.yml"))

    # copy docs templates from aplet application into projectfolder
    lektortemplates_path = pkg_resources.resource_filename(__name__, 'templates/lektor')
    doc_templates_path = path.join(projectfolder, "doc_templates")
    if not path.exists(doc_templates_path):
        shutil.copytree(lektortemplates_path, doc_templates_path)


@cli.command()
@click.option("--projectfolder", default=".", help="Location to output the aplet files")
@click.argument("product")
@click.argument("app_dir")
def runtests(projectfolder, product, app_dir):
    """ Runs the tests for a given product.
    Outputs the report files to a folder for later use.
    TODO: Should be able to run for all tests.
    """

    featuremodel_path = path.join(projectfolder, "productline", "model.xml")
    configs_path = path.join(projectfolder, "productline", "configs")
    testreports_path = path.join(projectfolder, "testreports")

    if not path.exists(testreports_path):
        makedirs(testreports_path)

    # TODO: needs some rethinking.  Where should we pick up the running app from?
    product_config_file_path = path.join(configs_path, product + ".config")
    shutil.copyfile(product_config_file_path, path.join(app_dir, "todo.config"))

    feature_toggles = []
    with open(product_config_file_path, "r") as product_config_file:
        product_features = [feature.strip() for feature in product_config_file.readlines()]
        feature_toggles = [feature.strip() for feature in product_features]
        optionals = plutils.find_optional_features(featuremodel_path)
        not_features = ["Not" + feature for feature in set(optionals) - set(product_features)]
        feature_toggles.extend(not_features)

    test_runner_conf = CONFIG['test_runner']
    click.echo("Running tests with {0}".format(test_runner_conf['name']))

    chdir(projectfolder)
    cmd_list = [test_runner_conf['command']]
    cmd_list.extend(test_runner_conf['arguments'])

    for feature_toggle in feature_toggles:
        cmd_list.append(test_runner_conf['feature_include_switch'])
        cmd_list.append(feature_toggle)

    click.echo("Running command" + subprocess.list2cmdline(cmd_list))
    subprocess.call(cmd_list)

    # copying report file for product
    testreport_path_without_ext = path.join(testreports_path, "report" + product)
    shutil.copyfile("tests/_output/report.json", path.join(testreport_path_without_ext + ".json"))
    shutil.copyfile("tests/_output/report.html", path.join(testreport_path_without_ext + ".html"))
    shutil.copyfile("tests/_output/report.xml", path.join(testreport_path_without_ext + ".xml"))

    chdir("..")


@cli.command()
@click.option("--docsfolder", default="./docs/generated")
@click.option("--port", default=9000)
def servedocs(docsfolder, port):
    """ Run a simple webserver serving the static files generated by makedocs.
    """
    chdir(docsfolder)
    server_address = ('localhost', port)
    httpd = HTTPServer(server_address, SimpleHTTPRequestHandler)

    click.echo("Serving at port {0}".format(port))
    httpd.serve_forever()


@cli.command()
@click.option("--projectfolder", default=".", help="Location to output the aplet files")
def makedocs(projectfolder):
    """ Generate the aplet documentation.
    Builds the docs from lektor templates incorporating test results from test runs in.
    """
    featuremodel_path = path.join(projectfolder, "productline", "model.xml")
    configs_path = path.join(projectfolder, "productline", "configs")
    bddfeatures_path = path.join(projectfolder, "bddfeatures")
    testreports_path = path.join(projectfolder, "testreports")
    feature_tree_renderer = ftrenderer.FeatureTreeRenderer()

    docs_dir = path.join(projectfolder, "docs/generated")
    if path.exists(docs_dir):
        shutil.rmtree(docs_dir)
    makedirs(docs_dir)

    lektor_templates_path = "doc_templates"
    utilities.sed_inplace(
        path.join(lektor_templates_path, "aplet.lektorproject"),
        r'<<PROJECT>>',
        CONFIG["project_name"])

    products = {}
    product_names = [path.splitext(product_path)[0] for product_path in listdir(configs_path)]
    for product_name in product_names:
        productconfig_filepath = path.join(projectfolder, "productline/configs", product_name + ".config")

        with open(productconfig_filepath, "r") as productconfig_file:
            products[product_name] = {}
            products[product_name]['features'] = [feature.strip() for feature in productconfig_file.readlines()]

        current_product_lektor_dir = path.join(lektor_templates_path, "content/products", product_name)
        if not path.exists(current_product_lektor_dir):
            makedirs(current_product_lektor_dir)

        product_filepath = path.join(current_product_lektor_dir,"contents.lr")
        shutil.copyfile(path.join(lektor_templates_path, "helpers/product_contents.lr"), product_filepath)

        utilities.sed_inplace(product_filepath, r'<<PRODUCT>>', product_name)
        product_test_status = ftrenderer.product_test_status(testreports_path, product_name)
        utilities.sed_inplace(product_filepath, "<<TEST_STATUS>>", product_test_status.name)

        feature_tree_renderer.generate_feature_tree_diagram(featuremodel_path, bddfeatures_path, testreports_path, productconfig_filepath)
        feature_tree_renderer.render_as_svg(current_product_lektor_dir, "feature_model")

        # Copy test run html report to generated docs
        product_report_name = "report{0}.html".format(product_name)
        shutil.copyfile(
            path.join(testreports_path, product_report_name),
            path.join(current_product_lektor_dir, product_report_name))

    click.echo("- Generating feature model SVG...")
    click.echo(featuremodel_path)
    feature_tree_renderer.generate_feature_tree_diagram(featuremodel_path, bddfeatures_path, testreports_path, "all")
    feature_tree_renderer.render_as_svg(path.join(lektor_templates_path, "content/"), "feature_model")

    click.echo("- Building site")
    lektor_cmd = ["lektor", "--project", lektor_templates_path, "build", "-O", path.abspath(docs_dir)]
    click.echo("Running: " + subprocess.list2cmdline(lektor_cmd))
    subprocess.call(lektor_cmd)

    product_map_renderer = mapbuilder.ProductMapRenderer()
    productline_generated_filepath = path.join(docs_dir, "index.html")
    html = product_map_renderer.get_productmap_html(featuremodel_path, products)
    utilities.sed_inplace(productline_generated_filepath, r'<<PRODUCTMAP>>', html)
