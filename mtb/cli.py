import os
from pathlib import Path
import click


@click.group()
def cli():
    pass


@cli.command()
@click.argument("args", nargs=-1)
def gui(args):
    "Start GUI with given model"
    print(f"Starting GUI")
    gui_path = Path(__file__).parent / "gui.py"
    # exec(open(path).read())
    os.system(f"python {gui_path} {' '.join(args)}")


def run():
    cli()
