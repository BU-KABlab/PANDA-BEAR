import pathlib
import typing
from pydantic import ConfigDict, FilePath
print()
print()
## get the current directory
desired = pathlib.Path.cwd() / 'code/config' / 'mill_config.json'
isinstance(desired, FilePath)