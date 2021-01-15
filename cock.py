from collections import ChainMap
from functools import reduce
from pathlib import Path
from typing import Any, Callable, List

import click
import yaml
from sortedcontainers import SortedDict

__all__ = ("build_entrypoint", "build_options_from_dict", "Option")
__version__ = "0.7.0"
version = tuple(map(int, __version__.split(".")))


class Config(SortedDict):

    def __getattr__(self, name: str) -> Any:
        return self[name]


def _gen_flat(d: dict, *, prefix="") -> dict:
    for k, v in d.items():
        current_prefix = "-".join(v for v in (prefix, k) if v)
        if isinstance(v, dict):
            yield from _gen_flat(v, prefix=current_prefix)
        else:
            yield current_prefix, v


def _build_file_args(configuration_file: Path) -> List[Any]:
    file_options = []
    raw = yaml.safe_load(configuration_file.read_text())
    viewed = set()
    for k, v in _gen_flat(raw):
        if k in viewed:
            raise ValueError(f"Key {k!r} already exist")
        viewed.add(k)
        if not isinstance(v, list):
            v = [v]
        for lv in v:
            file_options.extend([f"--{k}", lv])
    return file_options


def _decorate(decorators, f):
    return reduce(lambda f, d: d(f), decorators, f)


class Option:

    def __init__(self, **arguments):
        self.arguments = arguments


def _gen_dict_options(options: dict, *, subpath=()):
    for key, value in options.items():
        if isinstance(value, Option):
            full_key = "--" + "-".join(subpath + (key,))
            yield click.option(full_key, **value.arguments)
        elif isinstance(value, dict):
            yield from _gen_dict_options(value, subpath=subpath + (key,))
        else:
            raise ValueError(f"Expect dict or option, got {value!r}")


def build_options_from_dict(options: dict):
    return list(_gen_dict_options(options))


def build_entrypoint(main: Callable[[Config], Any], options: List[click.option],
                     **context_settings) -> Callable[..., Any]:
    decorators = [
        click.command(context_settings=context_settings),
        click.argument("configuration-file", default=None, required=False,
                       type=click.Path(exists=True, dir_okay=False, readable=True, resolve_path=True))
    ]
    decorators.extend(options)

    def entrypoint(**cli_options):
        file_options = {}
        configuration_file = cli_options["configuration_file"]
        if configuration_file:
            file_args = _build_file_args(Path(configuration_file))
            collector = _decorate(decorators, lambda **options: options)
            file_options = collector.main(args=file_args, standalone_mode=False, **context_settings)
        config = Config(**ChainMap(file_options, cli_options))
        return main(config)

    decorated_entrypoint = _decorate(decorators, entrypoint)
    return decorated_entrypoint
