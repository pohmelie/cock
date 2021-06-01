from textwrap import dedent

import click
import pytest
from click.testing import CliRunner

from cock import build_entrypoint, build_options_from_dict, Option


@pytest.fixture(scope="function")
def runner(request):
    return CliRunner()


options = [
    click.option("--a-b-c", default="abc-default"),
    click.option("--b-c-d", default=666, type=int),
    click.option("--c-d-e", multiple=True),
]


def test_defaults(runner):
    def main(config):
        assert config.a_b_c == "abc-default"
        assert config.b_c_d == 666
        assert config.c_d_e == ()
        assert config.configuration_file is None
        assert len(config) == 4
    ep = build_entrypoint(main, options)
    runner.invoke(ep, [], catch_exceptions=False)


def test_config(runner, tmp_path):
    def main(config):
        assert config.a_b_c == "abc-config"
        assert config.b_c_d == 667
        assert config.c_d_e == ("a", "b")
        assert config.configuration_file == str(config_path)
    config_path = tmp_path / "config.yml"
    ep = build_entrypoint(main, options)
    config_path.write_text(dedent("""\
        a:
          b:
            c: abc-config
        b-c:
          d: "667"
        c-d-e:
          - a
          - b
    """))
    runner.invoke(ep, [str(config_path)], catch_exceptions=False)


def test_config_duplicate(runner, tmp_path):
    def main(config):
        assert config.a_b_c == "abc-config"
        assert config.b_c_d == 667
    config_path = tmp_path / "config.yml"
    ep = build_entrypoint(main, options)
    config_path.write_text(dedent("""\
        a:
          b:
            c: abc-config
        a-b-c: fail
    """))
    with pytest.raises(ValueError):
        runner.invoke(ep, [str(config_path)], catch_exceptions=False)


def test_dictinary_configuration(runner):
    def main(config):
        assert config.a_b_c == "abc_default"
    dict_options = {
        "a": {
            "b": {
                "c": Option(default="abc-default"),
            },
        },
    }
    ep = build_entrypoint(main, build_options_from_dict(dict_options))
    runner.invoke(ep)


def test_dictinary_configuration_fail(runner):
    def main(config):
        assert config.a_b_c == "abc_default"
    dict_options = {
        "a": {
            "b": {
                "c": "fail",
            },
        },
    }
    with pytest.raises(ValueError):
        build_entrypoint(main, build_options_from_dict(dict_options))
