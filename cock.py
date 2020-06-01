from collections import ChainMap
from functools import reduce
from pathlib import Path
from typing import Any, Callable, List

import click
import yaml
from addict import Dict as AdDict

__all__ = ("build_entrypoint",)
__version__ = "0.2.0"
version = tuple(map(int, __version__.split(".")))


def _gen_flat(d: dict, *, prefix="") -> dict:
    for k, v in d.items():
        current_prefix = "-".join(v for v in (prefix, k) if v)
        if isinstance(v, dict):
            yield from _gen_flat(v, prefix=current_prefix)
        else:
            yield current_prefix, v


def _build_file_args(configuration_file: Path) -> AdDict:
    file_options = []
    raw = yaml.safe_load(configuration_file.read_text())
    pairs = list(_gen_flat(raw))
    viewed = set()
    for k, v in pairs:
        if k in viewed:
            raise ValueError(f"Key {k!r} already exist")
        viewed.add(k)
        file_options.extend([f"--{k}", v])
    return file_options


def _decorate(decorators, f):
    return reduce(lambda f, d: d(f), decorators, f)


def build_entrypoint(main: Callable[[AdDict], Any], options: List[click.option],
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
            file_options = collector.main(args=file_args, standalone_mode=False)
        config = AdDict(**ChainMap(file_options, cli_options))
        return main(config)

    decorated_entrypoint = _decorate(decorators, entrypoint)
    return decorated_entrypoint
