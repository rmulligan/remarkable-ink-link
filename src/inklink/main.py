"""Entry point for InkLink application."""

import click
from inklink.config import CONFIG


@click.group()
def cli():
    """InkLink CLI entry point."""
    pass


@cli.command()
@click.option("--host", default=CONFIG.get("HOST", "0.0.0.0"), help="Server host")
@click.option("--port", default=CONFIG.get("PORT", 9999), help="Server port", type=int)
def server(host, port):
    """Run the InkLink HTTP server."""
    from inklink.server import run_server

    run_server(host, port)


@cli.command()
@click.option("--host", default="127.0.0.1", help="Auth UI host")
@click.option("--port", default=8000, help="Auth UI port", type=int)
def auth(host, port):
    """Start the reMarkable Cloud authentication UI."""
    import uvicorn
    from inklink.auth import app

    uvicorn.run(app, host=host, port=port)


@cli.command()
@click.argument("input_file", type=click.Path(exists=True))
@click.option("--output", "-o", help="Output file name (optional)")
def roundtrip(input_file, output):
    """Process a handwritten query and generate a response."""
    from inklink.services.round_trip_service import RoundTripService
    
    service = RoundTripService()
    success, result = service.process_handwritten_query(input_file)
    
    if success:
        click.echo(f"Round-trip processing successful!")
        click.echo(f"Recognized text: {result['recognized_text']}")
        click.echo(f"Response uploaded to reMarkable: {result['upload_message']}")
        
        # Save to output file if specified
        if output:
            with open(output, "w") as f:
                f.write(f"Query: {result['recognized_text']}\n\n")
                f.write(f"Response: {result['response_text']}")
            click.echo(f"Response saved to {output}")
    else:
        click.echo(f"Error: {result['error']}")


def main():
    """Entry point for the application."""
    cli()


if __name__ == "__main__":
    main()
