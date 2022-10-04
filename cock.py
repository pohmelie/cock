from collections import ChainMap
from functools import reduce
from pathlib import Path
from typing import Any, Callable, Iterator, List, Tuple, Union

import click
import yaml
from sortedcontainers import SortedDict

__all__ = ("build_entrypoint", "build_options_from_dict", "get_options_defaults", "Config", "Option")
__version__ = "0.11.0"
version = tuple(map(int, __version__.split(".")))


class Config(SortedDict):

    def __getattr__(self, name: str) -> Any:
        return self[name]


class Option:

    def __init__(self, name: Union[str, None] = None, **attributes):
        if "required" in attributes:
            raise ValueError("`required` attribute is not allowed")
        self._name = None
        if name is not None:
            self.name = name
        self.attributes = attributes

    @property
    def name(self) -> str:
        if self._name is None:
            raise RuntimeError("Want to get `name`, but it is not set")
        return self._name

    @name.setter
    def name(self, value: str):
        if self._name is not None:
            raise RuntimeError(f"Want to set `name` to {value!r}, but `name` already set to {self._name!r}")
        self._name = value.replace("-", "_")

    @property
    def key(self) -> str:
        return "--" + self.name.replace("_", "-")

    def render(self) -> click.option:
        return click.option(self.key, **self.attributes)


def build_entrypoint(main: Callable[[Config], Any],
                     *options_stack: Union[dict, List[Union[Option, click.option]]],
                     **context_settings) -> Callable[..., Any]:
    options = []
    for item in options_stack:
        if isinstance(item, dict):
            item = build_options_from_dict(item)
        for option in item:
            if isinstance(option, Option):
                option = option.render()
            options.append(option)

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
            file_options["configuration_file"] = configuration_file
        config = Config(**ChainMap(file_options, cli_options))
        return main(config)

    decorated_entrypoint = _decorate(decorators, entrypoint)
    return decorated_entrypoint


def get_options_defaults(*options_stack: Union[dict, List[Option]]) -> Config:
    config = Config()
    for item in options_stack:
        if isinstance(item, dict):
            item = build_options_from_dict(item)
        for option in item:
            if not isinstance(option, Option):
                raise TypeError(f"Expect `Option`, got {option!r} of type {type(option)!r}")
            if "default" in option.attributes:
                if option.name in config:
                    raise RuntimeError(f"Key {option.name!r} already exist")
                config[option.name] = option.attributes["default"]
    return config


def build_options_from_dict(options: dict) -> List[Option]:
    return list(_gen_dict_options(options))


def _gen_dict_options(options: dict, *, name_parts=()) -> Iterator[Option]:
    for part, value in options.items():
        if isinstance(value, Option):
            name = "_".join(name_parts + (part,))
            value.name = name
            yield value
        elif isinstance(value, dict):
            yield from _gen_dict_options(value, name_parts=name_parts + (part,))
        else:
            raise TypeError(f"Expect `dict` or `Option`, got {value!r} of type {type(value)!r}")


def _decorate(decorators, f):
    return reduce(lambda f, d: d(f), decorators, f)


def _build_file_args(configuration_file: Path) -> List[str]:
    file_options = []
    raw = yaml.safe_load(configuration_file.read_text())
    viewed = set()
    for k, v in _gen_flat(raw):
        if k in viewed:
            raise RuntimeError(f"Key {k!r} already exist")
        viewed.add(k)
        if not isinstance(v, list):
            v = [v]
        for lv in v:
            file_options.extend([f"--{k}", lv])
    return file_options


def _gen_flat(d: dict, *, parts=()) -> Iterator[Tuple[str, Option]]:
    for k, v in d.items():
        current_parts = parts + (k,)
        if isinstance(v, dict):
            yield from _gen_flat(v, parts=current_parts)
        else:
            key = "-".join(current_parts)
            yield key.replace("_", "-"), v
