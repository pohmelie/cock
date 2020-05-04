from collections import ChainMap
from functools import reduce
from pathlib import Path
from typing import Any, Callable, List

import click
import yaml
from addict import Dict as AdDict

__all__ = ("build_entrypoint",)
__version__ = "0.1.0"
version = tuple(map(int, __version__.split(".")))


def _gen_flat(d: dict, *, prefix="") -> dict:
    for k, v in d.items():
        current_prefix = "_".join(v for v in (prefix, k) if v)
        if isinstance(v, dict):
            yield from _gen_flat(v, prefix=current_prefix)
        else:
            yield current_prefix.replace("-", "_"), v


def build_config(cli_options: dict) -> AdDict:
    file_options = {}
    if cli_options["configuration_file"]:
        path = Path(cli_options["configuration_file"])
        raw = yaml.safe_load(path.read_text())
        pairs = list(_gen_flat(raw))
        viewed = set()
        for k, _ in pairs:
            if k in viewed:
                raise ValueError(f"Key {k!r} already exist")
            viewed.add(k)
        file_options = dict(pairs)
    return AdDict(**ChainMap(file_options, cli_options))


def build_entrypoint(main: Callable[[AdDict], Any], options: List[click.option],
                     **context_settings) -> Callable[..., Any]:
    decorators = [
        click.command(context_settings=context_settings),
        click.argument("configuration-file", default=None, required=False,
                       type=click.Path(exists=True, dir_okay=False, readable=True, resolve_path=True))
    ]
    decorators.extend(options)

    def entrypoint(**cli_options):
        config = build_config(cli_options)
        return main(config)

    decorated_entrypoint = reduce(lambda f, d: d(f), decorators, entrypoint)
    return decorated_entrypoint
