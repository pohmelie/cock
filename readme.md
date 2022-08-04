# Cock
[Github actions status for master branch](https://github.com/pohmelie/cock/actions/workflows/ci.yml/badge.svg?branch=master)
[![Codecov coverage for master branch](https://codecov.io/gh/pohmelie/cock/branch/master/graph/badge.svg)](https://codecov.io/gh/pohmelie/cock)
[![Pypi version](https://img.shields.io/pypi/v/cock.svg)](https://pypi.org/project/cock/)
[![Pypi downloads count](https://img.shields.io/pypi/dm/cock)](https://pypi.org/project/cock/)

Cock stands for «**co**nfiguration file with cli**ck**». It is a configuration aggregator, which stands on shiny [`click`](https://github.com/pallets/click) library.

# Reason
No module for click with flat configuration file, which will mimic actual click options. There are [`click-config`](https://pypi.org/project/click-config) and [`click-config-file`](https://pypi.org/project/click-config-file), but they targets another goals.

# Features
- Aggregate configuration file and cli options into flat configuration object.
- Respect all click checks and conversions.
- `dict`-like, flat, sorted, dot-accessed configuration object.
- Entrypoint builder.

# License
`cock` is offered under MIT license.

# Requirements
* python 3.7+

# Usage
`example.py`:
``` python
import click

from cock import build_entrypoint, Config


def main(config: Config):
    print(config)


options = [
    click.option("--a-b-c", default="foo"),
    click.option("--b-c-d", default="bar"),
]
entrypoint = build_entrypoint(main, options, auto_envvar_prefix="EXAMPLE", show_default=True)

if __name__ == "__main__":
    entrypoint(prog_name="example")
```
This is almost pure click setup
```
$ python example.py --help
Usage: example [OPTIONS] [CONFIGURATION_FILE]

Options:
  --a-b-c TEXT  [default: foo]
  --b-c-d TEXT  [default: bar]
  --help        Show this message and exit.  [default: False]
```
But there is a `CONFIGURATION_FILE` argument. Lets see use cases.
### All deafults
```
$ python example.py
{'configuration_file': None, 'a_b_c': 'foo', 'b_c_d': 'bar'}
```
### From environment variable
```
$ EXAMPLE_A_B_C=foo-env python example.py
{'configuration_file': None, 'a_b_c': 'foo-env', 'b_c_d': 'bar'}
```
### From cli arguments
```
$ EXAMPLE_A_B_C=foo-env python example.py --a-b-c foo-cli
{'a_b_c': 'foo-cli', 'configuration_file': None, 'b_c_d': 'bar'}
```
### From configuration
`config-example.yml`:
``` yaml
a-b-c: foo-file
```
```
$ EXAMPLE_A_B_C=foo-env python example.py --a-b-c foo-cli config-example.yml
{'a_b_c': 'foo-file', 'configuration_file': '/absolute/path/to/config-example.yml', 'b_c_d': 'bar'}
```

Priority is obvious: **file > cli arguments > env variables**

As described in features paragraph, configuration is flattened before chaining with click options. So all configuration files listed below are equal:
``` yaml
a-b-c: foo-file
```
``` yaml
a:
  b:
    c: foo-file
```
``` yaml
a-b:
  c: foo-file
```
If provided file have key crossings:
``` yaml
a-b-c: foo-file1
a:
  b-c: foo-file2
```
Then `ValueError` will be raised.

`cock` uses `pyyaml` library for config loading, so it supports `yaml` and `json` formats, but this can be improved later if someone will need more configuration file types.

Configuration can be defined as dictionary too
``` python
from cock import build_entrypoint, build_options_from_dict, Option, Config


def main(config: Config):
    print(config)


options = {
    "a": {
        "b": {
            "c": Option(default="foo"),
        },
    },
}
entrypoint = build_entrypoint(main, build_options_from_dict(options), auto_envvar_prefix="EXAMPLE", show_default=True)

if __name__ == "__main__":
    entrypoint(prog_name="example")
```

You can also gather all defaults from dictionary defined options as a `Config`
``` python
from cock import get_options_defaults, Option

options = {
    "a": {
        "b": {
            "c": Option(default="foo"),
        },
    },
}
config = get_options_defaults(options)
assert config == {"a_b_c": "foo"}
assert config.a_b_c == "foo"
```

`Config` is an extended (with dot-access) version of `sortedcontainers.SortedDict`
``` python
>>> from cock import Config
>>> c = Config(b=1, a=2)
Config({'a': 2, 'b': 1})
>>> c["a"], c.b
(2, 1)
>>> c.z
...
KeyError: 'z'
>>> c.items()
SortedItemsView(Config({'a': 2, 'b': 1}))
>>> c["0"] = 0
>>> c
Config({'0': 0, 'a': 2, 'b': 1})
```

# API
``` python
def build_entrypoint(
    main: Callable[[Config], Any],
    options: List[click.option],
    **context_settings
) -> Callable[..., Any]:
```
* `main` is a user-space function of exactly one argument, a dot-accessed config wrapper.
* `options` is an iterable of `click.option` **decorators**.
* `**context_settings` is a dict passed through to `command` decorator.
