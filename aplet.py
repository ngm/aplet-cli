import click
import os
import shutil

@click.group()
def aplet():
    pass


@aplet.command()
@click.option("--projectfolder", default=".", help="Location to output the aplet files")
def init(**kwargs):
    os.mkdir("productline")
    shutil.copyfile("templates/model.xml", os.path.join(kwargs['projectfolder'], "productline/model.xml"))
    os.mkdir("productline/configs")
    shutil.copyfile("templates/ExampleProduct.config", os.path.join(kwargs['projectfolder'], "productline/configs/ExampleProduct.config"))


if __name__ == '__main__':
    aplet()

