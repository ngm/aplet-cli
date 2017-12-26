from aplet import parsefm
from aplet import utilities
from os import listdir, path, makedirs, chdir
import click
import pkg_resources
import shutil
import subprocess
import yaml

config = {}

def load_config(filename):
    with open(filename, "r") as stream:
        try:
            global config
            config = yaml.load(stream)
        except yaml.YAMLError as ex:
            print(ex)


@click.group()
@click.option("--configfile", default="./aplet.yml")
def cli(configfile):
    if path.exists(configfile):
        load_config("aplet.yml")
    pass

@cli.command()
def showconfig():
    print(yaml.dump(config))

@cli.command()
@click.option("--projectfolder", default=".", help="Location to output the aplet files")
def init(projectfolder):
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
    featuremodel_path = path.join(projectfolder, "productline", "model.xml")
    configs_path = path.join(projectfolder, "productline", "configs")
    bddfeatures_path = path.join(projectfolder, "bddfeatures")
    testreports_path = path.join(projectfolder, "testreports")

    if not path.exists(testreports_path):
        makedirs(testreports_path)

    # TODO: needs some rethinking.  Where should we pick up the running app from?
    product_config_file_path = path.join(configs_path, product + ".config")
    shutil.copyfile(product_config_file_path, path.join(app_dir, "todo.config"))

    feature_toggles = []
    with open(product_config_file_path, "r") as product_config_file:
        product_features = product_config_file.readlines()
        feature_toggles = [feature.strip() for feature in product_features]
        optionals = parsefm.find_optional_features(featuremodel_path)
        not_features = ["Not" + feature for feature in set(optionals) - set(product_features)]
        feature_toggles.extend(not_features)

    test_runner_conf = config['test_runner']
    click.echo("Running tests with {0}".format(test_runner_conf['name']))

    chdir(projectfolder)
    cmd_list = [test_runner_conf['command']]
    cmd_list.extend(test_runner_conf['arguments'])

    for feature_toggle in feature_toggles:
        cmd_list.append(test_runner_conf['feature_include_switch'])
        cmd_list.append(feature_toggle)

    click.echo("Running command" + subprocess.list2cmdline(cmd_list))
    subprocess.call(cmd_list)

    #python3 scripts/product_has_failed.py tests/_output/reports/ $PRODUCT
    #if [ $? -eq 0 ]; then
    #    sed -i "s/<<PASS_STATUS>>/true/g" build/lektor/content/products/$PRODUCT/contents.lr;
    #else
    #    sed -i "s/<<PASS_STATUS>>/false/g" build/lektor/content/products/$PRODUCT/contents.lr;
    #fi

    # copying report file for product
    shutil.copyfile("tests/_output/report.json", path.join("..", testreports_path, "report" + product + ".json"))
    shutil.copyfile("tests/_output/report.html", path.join("..", testreports_path, "report" + product + ".html"))
    shutil.copyfile("tests/_output/report.xml", path.join("..", testreports_path, "report" + product + ".xml"))

    chdir("..")


def get_product_map(products):
    html = "<table>"
    for product_name, product in products.items():
        html += "<tr><td>"
        html += product_name
        html += "</td></tr>"

    html += "<table>"

    return html


@cli.command()
@click.option("--projectfolder", default=".", help="Location to output the aplet files")
@click.option("--runtests/--no-runtests", default=False)
def makedocs(projectfolder, runtests):
    featuremodel_path = path.join(projectfolder, "productline", "model.xml")
    configs_path = path.join(projectfolder, "productline", "configs")
    bddfeatures_path = path.join(projectfolder, "bddfeatures")
    testreports_path = path.join(projectfolder, "testreports")

    docs_dir = path.join(projectfolder, "docs/generated")
    if path.exists(docs_dir):
        shutil.rmtree(docs_dir)
    makedirs(docs_dir)

    lektor_templates_path = "doc_templates"
    utilities.sed_inplace(path.join(lektor_templates_path, "aplet.lektorproject"), r'<<PROJECT>>', config["project_name"])

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

        parsefm.parse_feature_model(featuremodel_path, bddfeatures_path, testreports_path, productconfig_filepath, current_product_lektor_dir, "feature_model")

    click.echo("- Generating feature model SVG...")
    click.echo(featuremodel_path)
    parsefm.parse_feature_model(featuremodel_path, bddfeatures_path, testreports_path, "all", path.join(lektor_templates_path, "content/"), "feature_model")

    click.echo("- Building site")
    lektor_cmd = ["lektor", "--project", lektor_templates_path, "build", "-O", path.abspath(docs_dir)]
    click.echo("Running: " + subprocess.list2cmdline(lektor_cmd))
    subprocess.call(lektor_cmd) 

    productline_generated_filepath = path.join(docs_dir, "index.html")
    html = parsefm.get_productmap_html(featuremodel_path, products)
    utilities.sed_inplace(productline_generated_filepath, r'<<PRODUCTMAP>>', html)



if __name__ == '__main__':
    load_config("aplet.yml")
    aplet()
