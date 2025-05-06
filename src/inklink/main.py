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
@click.option("--prompt", prompt="Prompt", help="Question to send to AI model.")
@click.option("--model", default=None, help="OpenAI model to use (overrides config).")
def ask(prompt, model):
    """Ask a question to the AI and upload the response as a .rm file."""
    # Lazy imports of services
    from inklink.services.ai_service import AIService
    from inklink.services.document_service import DocumentService
    from inklink.services.remarkable_service import RemarkableService
    # Query AI
    ai_service = AIService(model=model)
    answer = ai_service.ask(prompt)
    if not answer:
        click.echo("No response from AI.")
        return
    # Prepare structured content from answer
    paragraphs = [line for line in answer.splitlines() if line.strip()]
    content = {"title": "AI Response", "structured_content": [{"type": "paragraph", "content": p} for p in paragraphs]}
    # Create HCL and convert to .rm
    ds = DocumentService(CONFIG["TEMP_DIR"], CONFIG["DRAWJ2D_PATH"])
    hcl_path = ds.create_hcl("AI Response", None, content)
    if not hcl_path:
        click.echo("Failed to generate HCL for AI response.")
        return
    rm_path = ds.create_rmdoc(hcl_path, "AI Response")
    if not rm_path:
        click.echo("Failed to convert HCL to .rm file.")
        return
    # Upload to reMarkable
    rs = RemarkableService(CONFIG["RMAPI_PATH"], CONFIG["RM_FOLDER"])
    success, message = rs.upload(rm_path, content.get("title", "AI Response"))
    # Report result
    click.echo(message)


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
            try:
                with open(output, "w") as f:
                    f.write(f"Query: {result['recognized_text']}\n\n")
                    f.write(f"Response: {result['response_text']}")
                click.echo(f"Response saved to {output}")
            except (IOError, OSError) as e:
                click.echo(f"Error: Failed to write to {output}. {e}")
    else:
        click.echo(f"Error: {result['error']}")


def main():
    """Entry point for the application."""
    cli()


if __name__ == "__main__":
    main()
