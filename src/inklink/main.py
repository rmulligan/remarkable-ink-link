"""Entry point for InkLink application."""
import click
from inklink.config import CONFIG

@click.group()
def cli():
    """InkLink CLI entry point."""
    pass

@cli.command()
@click.option('--host', default=CONFIG.get('HOST', '0.0.0.0'), help='Server host')
@click.option('--port', default=CONFIG.get('PORT', 9999), help='Server port', type=int)
def server(host, port):
    """Run the InkLink HTTP server."""
    from inklink.server import run_server
    run_server(host, port)

@cli.command()
@click.option('--host', default='127.0.0.1', help='Auth UI host')
@click.option('--port', default=8000, help='Auth UI port', type=int)
def auth(host, port):
    """Start the reMarkable Cloud authentication UI."""
    import uvicorn
    from inklink.auth import app
    uvicorn.run(app, host=host, port=port)

if __name__ == '__main__':
    cli()

if __name__ == "__main__":
    main()