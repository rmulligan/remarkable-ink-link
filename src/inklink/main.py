"""Entry point for InkLink application."""

import click
from inklink.config import CONFIG
from typing import List


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
    content = {
        "title": "AI Response",
        "structured_content": [{"type": "paragraph", "content": p} for p in paragraphs],
    }
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


# Knowledge Index Notebook commands
@cli.command()
@click.option(
    "--entity-types",
    help="Comma-separated list of entity types to include",
    type=str,
)
@click.option(
    "--min-references",
    default=1,
    help="Minimum number of references for an entity to be included",
    type=int,
)
@click.option(
    "--no-upload",
    is_flag=True,
    help="Skip uploading to reMarkable Cloud",
)
def create_entity_index(entity_types, min_references, no_upload):
    """Create an entity index notebook in EPUB format."""
    from inklink.di.container import Container
    from inklink.services.knowledge_index_service import KnowledgeIndexService

    # Parse entity types if provided
    entity_type_list = None
    if entity_types:
        entity_type_list = [t.strip() for t in entity_types.split(",")]

    # Get service via dependency injection
    provider = Container.create_provider(CONFIG)
    index_service = provider.get(KnowledgeIndexService)

    click.echo(f"Creating entity index notebook...")

    success, result = index_service.create_entity_index(
        entity_types=entity_type_list,
        min_references=min_references,
        upload_to_remarkable=not no_upload,
    )

    if success:
        click.echo(f"Entity index created successfully!")
        click.echo(f"Entity count: {result.get('entity_count', 0)}")
        click.echo(f"Entity types: {', '.join(result.get('entity_types', []))}")
        click.echo(f"EPUB saved to: {result.get('path')}")

        if not no_upload and result.get("upload_result", {}).get("success"):
            click.echo(
                f"Uploaded to reMarkable: {result['upload_result'].get('message')}"
            )
    else:
        click.echo(f"Error: {result.get('error', 'Unknown error')}")


@cli.command()
@click.option(
    "--top-n",
    default=20,
    help="Number of top topics to include",
    type=int,
)
@click.option(
    "--min-connections",
    default=2,
    help="Minimum connections for a topic to be included",
    type=int,
)
@click.option(
    "--no-upload",
    is_flag=True,
    help="Skip uploading to reMarkable Cloud",
)
def create_topic_index(top_n, min_connections, no_upload):
    """Create a topic index notebook in EPUB format."""
    from inklink.di.container import Container
    from inklink.services.knowledge_index_service import KnowledgeIndexService

    # Get service via dependency injection
    provider = Container.create_provider(CONFIG)
    index_service = provider.get(KnowledgeIndexService)

    click.echo(f"Creating topic index notebook...")

    success, result = index_service.create_topic_index(
        top_n_topics=top_n,
        min_connections=min_connections,
        upload_to_remarkable=not no_upload,
    )

    if success:
        click.echo(f"Topic index created successfully!")
        click.echo(f"Topic count: {result.get('topic_count', 0)}")
        click.echo(f"EPUB saved to: {result.get('path')}")

        if not no_upload and result.get("upload_result", {}).get("success"):
            click.echo(
                f"Uploaded to reMarkable: {result['upload_result'].get('message')}"
            )
    else:
        click.echo(f"Error: {result.get('error', 'Unknown error')}")


@cli.command()
@click.option(
    "--no-upload",
    is_flag=True,
    help="Skip uploading to reMarkable Cloud",
)
def create_notebook_index(no_upload):
    """Create a notebook index in EPUB format."""
    from inklink.di.container import Container
    from inklink.services.knowledge_index_service import KnowledgeIndexService

    # Get service via dependency injection
    provider = Container.create_provider(CONFIG)
    index_service = provider.get(KnowledgeIndexService)

    click.echo(f"Creating notebook index...")

    success, result = index_service.create_notebook_index(
        upload_to_remarkable=not no_upload
    )

    if success:
        click.echo(f"Notebook index created successfully!")
        click.echo(f"Notebook count: {result.get('notebook_count', 0)}")
        click.echo(f"EPUB saved to: {result.get('path')}")

        if not no_upload and result.get("upload_result", {}).get("success"):
            click.echo(
                f"Uploaded to reMarkable: {result['upload_result'].get('message')}"
            )
    else:
        click.echo(f"Error: {result.get('error', 'Unknown error')}")


@cli.command()
@click.option(
    "--no-upload",
    is_flag=True,
    help="Skip uploading to reMarkable Cloud",
)
def create_master_index(no_upload):
    """Create a master index combining entity, topic, and notebook indices in EPUB format."""
    from inklink.di.container import Container
    from inklink.services.knowledge_index_service import KnowledgeIndexService

    # Get service via dependency injection
    provider = Container.create_provider(CONFIG)
    index_service = provider.get(KnowledgeIndexService)

    click.echo(f"Creating master index notebook...")

    success, result = index_service.create_master_index(
        upload_to_remarkable=not no_upload
    )

    if success:
        click.echo(f"Master index created successfully!")
        click.echo(f"Entity count: {result.get('entity_count', 0)}")
        click.echo(f"Topic count: {result.get('topic_count', 0)}")
        click.echo(f"Notebook count: {result.get('notebook_count', 0)}")
        click.echo(f"EPUB saved to: {result.get('path')}")

        if not no_upload and result.get("upload_result", {}).get("success"):
            click.echo(
                f"Uploaded to reMarkable: {result['upload_result'].get('message')}"
            )
    else:
        click.echo(f"Error: {result.get('error', 'Unknown error')}")


def main():
    """Entry point for the application."""
    cli()


if __name__ == "__main__":
    main()
