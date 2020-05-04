from textwrap import dedent

import click
import pytest
from click.testing import CliRunner

from cock import build_entrypoint


@pytest.fixture(scope="function")
def runner(request):
    return CliRunner()


options = [
    click.option("--a-b-c", default="abc-default"),
    click.option("--b-c-d", default=666, type=int),
]


def test_defaults(runner):
    def main(config):
        assert config.a_b_c == "abc-default"
        assert config.b_c_d == 666
        assert config.configuration_file is None
        assert len(config) == 3
    ep = build_entrypoint(main, options)
    runner.invoke(ep, [], catch_exceptions=False)


def test_config(runner, tmp_path):
    def main(config):
        assert config.a_b_c == "abc-config"
        assert config.b_c_d == 667
    config_path = tmp_path / "config.yml"
    ep = build_entrypoint(main, options)
    config_path.write_text(dedent("""\
        a:
          b:
            c: abc-config
        b-c:
          d: 667
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
