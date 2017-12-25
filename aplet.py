from os import listdir, path, makedirs, chdir
import click
import parsefm
import shutil
import subprocess
import utilities
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
def aplet():
    load_config("aplet.yml")
    pass

@aplet.command()
def showconfig():
    print(yaml.dump(config))

@aplet.command()
@click.option("--projectfolder", default=".", help="Location to output the aplet files")
def init(projectfolder):
    productline_dir = path.join(projectfolder, "productline")
    configs_path = path.join(productline_dir, "configs")
    bddfeatures_path = path.join(projectfolder, "bddfeatures")
    testreports_path = path.join(projectfolder, "testreports")

    if not path.exists(productline_dir):
        makedirs(productline_dir)
    shutil.copyfile("templates/model.xml", path.join(productline_dir, "model.xml"))

    if not path.exists(configs_path):
        makedirs(configs_path)
    shutil.copyfile("templates/ExampleProduct.config", path.join(configs_path, "ExampleProduct.config"))

    if not path.exists(bddfeatures_path):
        makedirs(bddfeatures_path)

    if not path.exists(testreports_path):
        makedirs(testreports_path)


@aplet.command()
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
        features = product_config_file.readlines()
        feature_toggles = [feature.strip() for feature in features]

        # TODO: add not toggles
        #not_feature_toggles = [" -g Not" + feature.strip() for feature in features]
        #export NOTFEATURES=$(comm -13 <(sort eclipse/configs/$PRODUCT.config) <(sort eclipse/configs/optionals.config) | sed 's?\(.*\)?-g Not\1 ?' | tr -d '\r\n')

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

    # copying report file for product
    shutil.copyfile("tests/_output/report.json", path.join("..", testreports_path, "report" + product + ".json"))
    shutil.copyfile("tests/_output/report.html", path.join("..", testreports_path, "report" + product + ".html"))
    shutil.copyfile("tests/_output/report.xml", path.join("..", testreports_path, "report" + product + ".xml"))

    chdir("..")


@aplet.command()
@click.option("--projectfolder", default=".", help="Location to output the aplet files")
@click.option("--runtests/--no-runtests", default=False)
def makedocs(projectfolder, runtests):
    featuremodel_path = path.join(projectfolder, "productline", "model.xml")
    configs_path = path.join(projectfolder, "productline", "configs")
    bddfeatures_path = path.join(projectfolder, "bddfeatures")
    testreports_path = path.join(projectfolder, "testreports")

    docs_dir = path.join(projectfolder, "docs")
    if not path.exists(docs_dir):
        makedirs(docs_dir)

    lektor_temp_dir = path.join(docs_dir, "lektor")
    if not path.exists(lektor_temp_dir):
        shutil.copytree("templates/lektor", lektor_temp_dir)
    utilities.sed_inplace(path.join(lektor_temp_dir, "aplet.lektorproject"), r'<<PROJECT>>', config["project_name"])

    products = [path.splitext(product_path)[0] for product_path in listdir(configs_path)]
    for product in products:
        #cp eclipse/configs/$PRODUCT.config $APP_DIR/todo.config
        #export FEATURES=$(sed 's?\(.*\)?-g \1 ?' eclipse/configs/$PRODUCT.config | tr -d '\r\n')
        #export NOTFEATURES=$(comm -13 <(sort eclipse/configs/$PRODUCT.config) <(sort eclipse/configs/optionals.config) | sed 's?\(.*\)?-g Not\1 ?' | tr -d '\r\n')

        if runtests:
            click.echo("Running tests")
            #php vendor/bin/codecept run acceptance $FEATURES $NOTFEATURES --debug --json --html --xml
            # copying report file for product
            #cp tests/_output/report.json tests/_output/reports/report$PRODUCT.json
            #cp tests/_output/report.xml tests/_output/reports/report$PRODUCT.xml
            #cp tests/_output/report.html tests/_output/reports/report$PRODUCT.html

        current_product_lektor_dir = path.join(lektor_temp_dir, "content/products", product)
        if not path.exists(current_product_lektor_dir):
            makedirs(current_product_lektor_dir)

        product_filepath = path.join(current_product_lektor_dir,"contents.lr")
        shutil.copyfile("templates/lektor/helpers/product_contents.lr", product_filepath)

        utilities.sed_inplace(product_filepath, r'<<PRODUCT>>', product)

        if runtests:
            click.echo("Running tests")
            #cp tests/_output/report.html build/lektor/content/products/$PRODUCT/report$PRODUCT.html

        #python3 scripts/product_has_failed.py tests/_output/reports/ $PRODUCT
        #if [ $? -eq 0 ]; then
        #    sed -i "s/<<PASS_STATUS>>/true/g" build/lektor/content/products/$PRODUCT/contents.lr;
        #else
        #    sed -i "s/<<PASS_STATUS>>/false/g" build/lektor/content/products/$PRODUCT/contents.lr;
        #fi
        product_config_file = path.join(projectfolder, "productline/configs", product + ".config")

        parsefm.parse_feature_model(featuremodel_path, bddfeatures_path, testreports_path, product_config_file, current_product_lektor_dir, "feature_model")

    click.echo("- Generating feature model SVG...")
    click.echo(featuremodel_path)
    parsefm.parse_feature_model(featuremodel_path, bddfeatures_path, testreports_path, "all", path.join(lektor_temp_dir, "content/"), "feature_model")

    click.echo("- Building site")
    chdir(lektor_temp_dir)
    subprocess.call(["lektor", "build", "-O" "out"]) 


if __name__ == '__main__':
    load_config("aplet.yml")
    aplet()
