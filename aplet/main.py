import shutil
import subprocess
from http.server import HTTPServer, SimpleHTTPRequestHandler
from os import chdir, listdir, makedirs, path

import click
import pkg_resources
import yaml

from aplet import utilities
from aplet.pltools import ftrenderer, mapbuilder, parsers
from aplet.pltools.parsers import FeatureModel, FeatureModelParser, ProductConfigParser


CONFIG = {}
RUNNING_TEST_PROCESSES = []


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
@click.option("--projectname", prompt="Project Name", default="My Product Line", help="Name to give the project")
@click.option("--example/--no-example", default=False, help="Whether to create example feature model and config files")
def init(projectfolder, projectname, example):
    """ Initialises an aplet project folder, containing example product line and docs templates.
    """

    productline_dir = path.join(projectfolder, "productline")
    configs_path = path.join(productline_dir, "configs")
    bddfeatures_path = path.join(projectfolder, "bddfeatures")
    testreports_path = path.join(projectfolder, "testreports")

    if not path.exists(productline_dir):
        makedirs(productline_dir)

    if not path.exists(configs_path):
        makedirs(configs_path)

    if not path.exists(bddfeatures_path):
        makedirs(bddfeatures_path)

    if not path.exists(testreports_path):
        makedirs(testreports_path)

    model_src = pkg_resources.resource_filename(__name__, "templates/model.xml")
    model_dst = path.join(productline_dir, "model.xml")
    shutil.copyfile(model_src, model_dst)
    utilities.sed_inplace(model_dst, "{{PROJECT_NAME}}", projectname.replace(" ", ""))

    configtemplate_src = pkg_resources.resource_filename(__name__, 'templates/aplet.yml')
    configtemplate_dst = path.join(projectfolder, "aplet.yml")
    shutil.copyfile(configtemplate_src, configtemplate_dst)
    utilities.sed_inplace(configtemplate_dst, "{{PROJECT_NAME}}", projectname)

    # copy docs templates from aplet application into projectfolder
    lektortemplates_path = pkg_resources.resource_filename(__name__, 'templates/lektor')
    doc_templates_path = path.join(projectfolder, "doc_templates")
    if not path.exists(doc_templates_path):
        shutil.copytree(lektortemplates_path, doc_templates_path)


    if example:
        examples_dir = "templates/exampleproject"
        model_src = pkg_resources.resource_filename(__name__, path.join(examples_dir, "model.xml"))
        shutil.copyfile(model_src, model_dst)
        exampleconfig_src = pkg_resources.resource_filename(__name__, path.join(examples_dir, "ExampleProduct.config"))
        shutil.copyfile(exampleconfig_src, path.join(configs_path, "ExampleProduct.config"))
        configtemplate_src = pkg_resources.resource_filename(__name__, path.join(examples_dir, "aplet.yml"))
        shutil.copyfile(configtemplate_src, configtemplate_dst)


def get_feature_toggles_for_testrunner(product_config_file_path, optional_features):
    with open(product_config_file_path, "r") as product_config_file:
        product_features = []
        product_features = [feature.strip() for feature in product_config_file.readlines()]
        feature_toggles = [feature.strip() for feature in product_features]
        optionals_names = [optional_feature.name for optional_feature in optional_features]
        not_features = ["Not" + feature for feature in set(optionals_names) - set(product_features)]
        feature_toggles.extend(not_features)

        return feature_toggles


def before_productline_steps():
    """ Steps that need running to set up the test environment for whole product line.
    """
    cmd = ['phantomjs', '--webdriver', '4444']
    click.echo("Running command" + subprocess.list2cmdline(cmd))
    process = subprocess.Popen(cmd)
    RUNNING_TEST_PROCESSES.append(process)


def before_product_steps(productconfig_filepath, productapp_path):
    """ Steps that need to run before an individual product is tested.
    """
    # TODO: this is product line specific and needs to be extracted
    shutil.copyfile(productconfig_filepath, path.join(productapp_path, "todo.config"))

    cmd = ['php', '-S', 'localhost:8080', '-t', productapp_path]
    process = subprocess.Popen(cmd)

    RUNNING_TEST_PROCESSES.append(process)


@cli.command()
@click.option("--projectfolder", default=".", help="Location to output the aplet files")
@click.option("--product", help="If provided, will run for single product.  Otherwise all products are tested")
@click.argument("app_dir")
def runtests(projectfolder, product, app_dir):
    """ Runs the tests for a given product.
    Outputs the report files to a folder for later use.
    TODO: Should be able to run for all products at once.
    """

    featuremodel_path = path.join(projectfolder, "productline", "model.xml")
    configs_path = path.join(projectfolder, "productline", "configs")
    testreports_path = path.join(projectfolder, "testreports")

    if not path.exists(testreports_path):
        makedirs(testreports_path)

    fmparser = parsers.FeatureModelParser()
    featuremodel = fmparser.parse_from_file(featuremodel_path)
    configparser = parsers.ProductConfigParser(featuremodel.root_feature.name)

    before_productline_steps()

    # Figure out which products to run for.
    product_names = []
    if product is None:
        product_names = get_product_names_from_configs_path(configs_path)
    else:
        product_names = [product]

    for product_name in product_names:
        productconfig_filepath = path.join(configs_path, product_name + ".config")

        before_product_steps(productconfig_filepath, app_dir)

        product_features = configparser.parse_config(productconfig_filepath)
        trimmed_featuremodel = featuremodel.get_copy_trimmed_based_on_config(product_features)
        feature_toggles = get_feature_toggles_for_testrunner(productconfig_filepath, featuremodel.optional_features())

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
        testreport_path_without_ext = path.join(testreports_path, "report" + product_name)
        shutil.copyfile("tests/_output/report.json", path.join(testreport_path_without_ext + ".json"))
        shutil.copyfile("tests/_output/report.html", path.join(testreport_path_without_ext + ".html"))
        shutil.copyfile("tests/_output/report.xml", path.join(testreport_path_without_ext + ".xml"))

    chdir("..")

    for process in RUNNING_TEST_PROCESSES:
        process.terminate()


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


def get_product_names_from_configs_path(configs_path):
    return [path.splitext(product_path)[0] for product_path in listdir(configs_path)]


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

    fmparser = parsers.FeatureModelParser()
    resultsparser = parsers.TestResultsParser()
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
    product_names = get_product_names_from_configs_path(configs_path)
    for product_name in product_names:
        productconfig_filepath = path.join(projectfolder, "productline/configs", product_name + ".config")
        product_html_report_name = "report{0}.html".format(product_name)
        product_html_results_src = path.join(testreports_path, product_html_report_name)
        product_xml_report_name = "report{0}.xml".format(product_name)
        product_xml_results_src = path.join(testreports_path, product_xml_report_name)

        with open(productconfig_filepath, "r") as productconfig_file:
            products[product_name] = {}
            products[product_name]['features'] = [feature.strip() for feature in productconfig_file.readlines()]

        current_product_lektor_dir = path.join(lektor_templates_path, "content/products", product_name)
        if not path.exists(current_product_lektor_dir):
            makedirs(current_product_lektor_dir)

        product_filepath = path.join(current_product_lektor_dir,"contents.lr")
        shutil.copyfile(path.join(lektor_templates_path, "helpers/product_contents.lr"), product_filepath)

        feature_model = fmparser.parse_from_file(featuremodel_path)
        gherkin_pieces = ftrenderer.gherkin_pieces_grouped_by_featurename(bddfeatures_path)
        gherkin_piece_test_statuses = resultsparser.get_gherkin_piece_test_statuses_for_product_from_file(product_xml_results_src)
        configparser = parsers.ProductConfigParser(feature_model.root_feature.name)
        product_features = configparser.parse_config(productconfig_filepath)
        feature_model.trim_based_on_config(product_features)
        feature_model.add_gherkin_pieces(gherkin_pieces)
        feature_model.calculate_test_statuses(gherkin_piece_test_statuses)

        feature_tree_renderer.build_graphviz_graph(feature_model.root_feature)
        feature_tree_renderer.render_as_svg(current_product_lektor_dir, "feature_model")

        utilities.sed_inplace(product_filepath, r'<<PRODUCT>>', product_name)
        product_test_status = feature_model.root_feature.test_status
        utilities.sed_inplace(product_filepath, "<<TEST_STATUS>>", product_test_status.name)

        # Copy test run html report to generated docs
        if path.exists(product_html_results_src):
            shutil.copyfile(product_html_results_src, path.join(current_product_lektor_dir, product_html_report_name))

    click.echo("- Generating feature model SVG...")
    click.echo(featuremodel_path)

    feature_model = fmparser.parse_from_file(featuremodel_path)
    gherkin_pieces = ftrenderer.gherkin_pieces_grouped_by_featurename(bddfeatures_path)
    gherkin_piece_test_statuses = resultsparser.get_gherkin_piece_test_statuses_for_dir(testreports_path)
    feature_model.add_gherkin_pieces(gherkin_pieces)
    feature_model.calculate_test_statuses(gherkin_piece_test_statuses)

    feature_tree_renderer.build_graphviz_graph(feature_model.root_feature)
    feature_tree_renderer.render_as_svg(path.join(lektor_templates_path, "content/"), "feature_model")

    click.echo("- Building site")
    lektor_cmd = ["lektor", "--project", lektor_templates_path, "build", "-O", path.abspath(docs_dir)]
    click.echo("Running: " + subprocess.list2cmdline(lektor_cmd))
    subprocess.call(lektor_cmd)

    product_map_renderer = mapbuilder.ProductMapRenderer()
    productline_generated_filepath = path.join(docs_dir, "index.html")
    html = product_map_renderer.get_productmap_html(feature_model, products)
    utilities.sed_inplace(productline_generated_filepath, r'<<PRODUCTMAP>>', html)
