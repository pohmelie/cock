from textwrap import dedent

import click
import pytest
from click.testing import CliRunner

from cock import Option, build_entrypoint, build_options_from_dict, get_options_defaults


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
        c_d-e:
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
        a-b_c: fail
    """))
    with pytest.raises(RuntimeError):
        runner.invoke(ep, [str(config_path)], catch_exceptions=False)


def test_dictionary_configuration(runner):
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


def test_dictionary_configuration_fail(runner):
    def main(config):
        assert config.a_b_c == "abc_default"
    dict_options = {
        "a": {
            "b": {
                "c": "fail",
            },
        },
    }
    with pytest.raises(TypeError):
        build_entrypoint(main, build_options_from_dict(dict_options))


def test_dictionary_defaults():
    dict_options = {
        "b": {
            "c": Option(),
        },
        "a": {
            "b": {
                "c": Option(default="abc-default"),
            },
        },
    }
    config = get_options_defaults(dict_options)
    assert config == {
        "a_b_c": "abc-default",
    }


def test_dictionary_defaults_fail():
    dict_options = {
        "a_b_c": Option(default="foo"),
        "a": {
            "b": {
                "c": Option(default="abc-default"),
            },
        },
    }
    with pytest.raises(RuntimeError):
        get_options_defaults(dict_options)


def test_required_argument():
    with pytest.raises(ValueError):
        Option(required=True)


def test_mix_options(runner):
    def main(config):
        assert config.a_b_c == "foo"
        assert config.a_b_d == "bar"
        assert config.a_b_e == "baz"
    dict_options = {"a_b_c": Option(default="foo")}
    list_options = [Option("a_b_d", default="bar"),
                    click.option("--a-b-e", default="baz")]
    ep = build_entrypoint(main, dict_options, list_options)
    runner.invoke(ep)


def test_get_defaults_mix():
    dict_options = {"a_b-c": Option(default="foo")}
    list_options = [Option("a-b_d", default="bar")]
    config = get_options_defaults(dict_options, list_options)
    assert config.a_b_c == "foo"
    assert config.a_b_d == "bar"


def test_option_corner_cases():
    list_options = [Option(default="bar")]
    with pytest.raises(RuntimeError):
        build_entrypoint(None, list_options)

    dict_options = {"a_b_c": Option("b_c_d", default="foo")}
    with pytest.raises(RuntimeError):
        build_entrypoint(None, dict_options)


def test_get_defaults_fail_on_click_option():
    list_options = [click.option("--foo", default="bar")]
    with pytest.raises(TypeError):
        get_options_defaults(list_options)
