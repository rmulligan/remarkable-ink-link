from click.testing import CliRunner


def test_cli_help():
    """Test that the CLI help message is displayed."""
    from inklink.main import cli

    runner = CliRunner()
    result = runner.invoke(cli, ["--help"])
    assert result.exit_code == 0
    assert "InkLink CLI entry point" in result.output
