import sys

try:
    from ._version import version as __version__
except ImportError:
    __version__ = "0.0.0"

def latigo_cli():
    """
    The main entry point for the CLI interface
    """
    if "--version" in sys.argv:
        print(__version__)
    else:
        print(f"usage: {sys.argv[0]} --version" )


if __name__ == "__main__":
    latigo_cli()
