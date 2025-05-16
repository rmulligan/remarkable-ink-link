"""Entry point for InkLink application."""

import json
import logging
import os
import subprocess
import time
from typing import Any, Dict

import click

from inklink.config import CONFIG


@click.group()
def cli():
    """InkLink CLI entry point."""


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
@click.option("--model", default=None, help="Claude model to use (overrides config).")
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
        click.echo("Round-trip processing successful!")
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

    click.echo("Creating entity index notebook...")

    success, result = index_service.create_entity_index(
        entity_types=entity_type_list,
        min_references=min_references,
        upload_to_remarkable=not no_upload,
    )

    if success:
        click.echo("Entity index created successfully!")
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

    click.echo("Creating topic index notebook...")

    success, result = index_service.create_topic_index(
        top_n_topics=top_n,
        min_connections=min_connections,
        upload_to_remarkable=not no_upload,
    )

    if success:
        click.echo("Topic index created successfully!")
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

    click.echo("Creating notebook index...")

    success, result = index_service.create_notebook_index(
        upload_to_remarkable=not no_upload
    )

    if success:
        click.echo("Notebook index created successfully!")
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

    click.echo("Creating master index notebook...")

    success, result = index_service.create_master_index(
        upload_to_remarkable=not no_upload
    )

    if success:
        click.echo("Master index created successfully!")
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


def update_knowledge_graph(
    image_path: str, response_text: str, notebook_info: Dict[str, Any]
) -> None:
    """
    Update the Neo4j knowledge graph with content from the image and Claude's response.

    Args:
        image_path: Path to the PNG image
        response_text: Claude's response text
        notebook_info: Dictionary with notebook metadata
    """
    try:
        # Import Neo4j knowledge graph tools from MCP
        from mcp__neo4j_knowledge__create_entities import create_entities
        from mcp__neo4j_knowledge__create_relations import create_relations

        # Extract basic information
        notebook_name = notebook_info.get("name", "Unnamed Notebook")
        page_name = os.path.basename(image_path)
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")

        # Create source entity for the notebook page
        notebook_entity = {
            "name": notebook_name,
            "entityType": "Notebook",
            "observations": [
                "Remarkable notebook processed by Cassidy assistant",
                f"Contains page: {page_name}",
                f"Last processed: {timestamp}",
            ],
        }

        # Create entity for the page
        page_entity = {
            "name": page_name,
            "entityType": "NotebookPage",
            "observations": [
                f"Page from notebook: {notebook_name}",
                f"Processed by Cassidy assistant on {timestamp}",
            ],
        }

        # Add entities to knowledge graph
        create_entities({"entities": [notebook_entity, page_entity]})

        # Create relationship between notebook and page
        create_relations(
            {
                "relations": [
                    {"from": notebook_name, "to": page_name, "relationType": "CONTAINS"}
                ]
            }
        )

        # Use Claude to extract entities from the response
        entities_prompt = f"""
        Analyze the following text and extract key entities (people, places, concepts, organizations, etc.).
        For each entity, provide its type and a brief description based on the context.

        TEXT:
        {response_text[:5000]}  # Limit text length for efficiency

        Format your response as a JSON array of objects, one per entity:
        [
            {{"name": "entity_name", "entityType": "entity_type", "description": "brief description"}},
            ...
        ]

        Only include the JSON array in your response, nothing else.
        """

        # Call Claude to extract entities
        claude_entities_result = subprocess.run(
            ["claude", "-b"],
            input=entities_prompt.encode("utf-8"),
            capture_output=True,
            text=True,
        )

        if claude_entities_result.returncode == 0:
            # Parse entities from Claude's response
            try:
                # Find JSON array in response (simple approach: find first [ and last ])
                entity_text = claude_entities_result.stdout
                start_idx = entity_text.find("[")
                end_idx = entity_text.rfind("]") + 1

                if start_idx >= 0 and end_idx > start_idx:
                    entities_json = entity_text[start_idx:end_idx]
                    entities = json.loads(entities_json)

                    # Add extracted entities to knowledge graph
                    kg_entities = []
                    relations = []

                    for entity in entities:
                        entity_name = entity.get("name")
                        entity_type = entity.get("entityType")
                        description = entity.get("description")

                        if entity_name and entity_type:
                            # Create entity
                            kg_entities.append(
                                {
                                    "name": entity_name,
                                    "entityType": entity_type,
                                    "observations": (
                                        [description] if description else []
                                    ),
                                }
                            )

                            # Create relationship to page
                            relations.append(
                                {
                                    "from": page_name,
                                    "to": entity_name,
                                    "relationType": "MENTIONS",
                                }
                            )

                    # Batch create entities and relations
                    if kg_entities:
                        create_entities({"entities": kg_entities})

                    if relations:
                        create_relations({"relations": relations})

                    print(
                        f"Added {len(kg_entities)} entities and {len(relations)} relationships to knowledge graph"
                    )
            except json.JSONDecodeError:
                print("Failed to parse entities from Claude's response")
            except Exception as e:
                print(f"Error processing entities: {str(e)}")
    except ImportError:
        print(
            "Neo4j knowledge graph tools not available, skipping knowledge graph update"
        )
    except Exception as e:
        print(f"Error in knowledge graph update: {str(e)}")


@cli.command()
@click.option("--interval", default=60, help="Polling interval in seconds", type=int)
@click.option("--tag", default="Lilly", help="Tag to search for", type=str)
@click.option("--rmapi", default=None, help="Path to rmapi executable", type=str)
@click.option(
    "--output-dir",
    default=None,
    help="Output directory for downloaded notebooks",
    type=str,
)
@click.option(
    "--claude-command", default="claude", help="Command to run Claude", type=str
)
@click.option(
    "--lilly-workspace",
    default=None,
    help="Path to Lilly's workspace directory",
    type=str,
)
@click.option("--once", is_flag=True, help="Run the check once and exit")
def lilly(interval, tag, rmapi, output_dir, claude_command, lilly_workspace, once):
    """Monitor reMarkable Cloud for notebooks tagged with 'Lilly' and process them with Claude vision."""
    from inklink.adapters.cassidy_adapter import CassidyAdapter
    from inklink.services.lilly_monitor_service import LillyMonitor

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    # Resolve rmapi path if not provided
    if not rmapi:
        rmapi = CONFIG.get("RMAPI_PATH")
        if not rmapi:

            home_dir = os.path.expanduser("~")
            potential_paths = [
                os.path.join(home_dir, "bin", "rmapi"),
                "/usr/local/bin/rmapi",
                "/usr/bin/rmapi",
            ]
            for path in potential_paths:
                if os.path.exists(path) and os.access(path, os.X_OK):
                    rmapi = path
                    break

    # Set default Lilly workspace if not provided
    if not lilly_workspace:
        lilly_workspace = os.path.join(
            os.path.dirname(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            ),
            "lilly",
        )

    # Initialize the adapter
    adapter = CassidyAdapter(rmapi_path=rmapi, tag=tag)

    # Define the callback function for when notebooks/pages are found
    def process_content(content_info):
        content_type = content_info.get("type", "unknown")

        if content_type == "notebook":
            print(
                f"Processed notebook: {content_info['name']} with {len(content_info.get('png_paths', []))} pages"
            )

            # If all pages were processed successfully, report success
            if content_info.get("all_pages_processed", False):
                print(
                    f"All pages processed successfully. Tag '{tag}' removed from notebook."
                )
            else:
                print(
                    f"Not all pages processed successfully. Tag '{tag}' retained for retry."
                )

        elif content_type == "page":
            print(
                f"Processed page {content_info.get('page_index')} in notebook: {content_info.get('doc_name')}"
            )
            print(f"Response saved to: {content_info.get('response_path')}")

        else:
            print(f"Processed content: {content_info}")

    # Create and start the monitor
    monitor = LillyMonitor(
        adapter=adapter,
        polling_interval=interval,
        output_dir=output_dir,
        tag=tag,
        callback=process_content,
        claude_command=claude_command,
        lilly_workspace=lilly_workspace,
    )

    if once:
        # Run once and print results
        print(f"Checking for notebooks tagged with '{tag}'...")
        notebooks = monitor.check_now()
        if notebooks:
            print(f"Found {len(notebooks)} tagged notebooks")
        else:
            print("No tagged notebooks found")
    else:
        # Run continuously
        print(f"Starting Lilly monitor for notebooks tagged with '{tag}'")
        print(f"Using Claude command: {claude_command}")
        print(f"Lilly workspace: {lilly_workspace}")
        print(f"Polling interval: {interval} seconds")
        print("Press Ctrl+C to stop")

        monitor.start()

        try:
            # Keep the main thread alive
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\nStopping Lilly monitor...")
        finally:
            monitor.stop()
            print("Lilly monitor stopped")


@cli.command()
@click.option(
    "--query-tag", default=CONFIG.get("LILLY_TAG", "Lilly"), help="Tag for query pages"
)
@click.option("--context-tag", default="Context", help="Tag for context pages")
@click.option("--kg-tag", default="kg", help="Tag for knowledge graph processing")
@click.option("--new-tag", default="new", help="Tag to start a new conversation")
@click.option(
    "--subject-tag",
    default=CONFIG.get("LILLY_SUBJECT_TAG", "Subject"),
    help="Tag prefix for subject classification",
)
@click.option(
    "--default-subject",
    default=CONFIG.get("LILLY_DEFAULT_SUBJECT", "General"),
    help="Default subject if none specified",
)
@click.option(
    "--use-subject-dirs/--no-subject-dirs",
    default=CONFIG.get("LILLY_USE_SUBJECT_DIRS", True),
    help="Organize notebooks into subject directories",
)
@click.option(
    "--pre-filter-tag",
    default=CONFIG.get("LILLY_PRE_FILTER_TAG", "HasLilly"),
    help="Document-level tag for pre-filtering notebooks",
)
@click.option(
    "--no-pre-filter",
    is_flag=True,
    help="Disable pre-filtering with document-level tag",
)
@click.option(
    "--mcp-tools",
    default="",
    help="Comma-separated list of MCP tools to support as tags",
)
@click.option(
    "--claude-command",
    default=CONFIG.get("CLAUDE_COMMAND", "/home/ryan/.claude/local/claude"),
    help="Command to run Claude with context by default",
)
@click.option(
    "--poll-interval",
    default=CONFIG.get("LILLY_POLLING_INTERVAL", 60),
    help="Poll interval in seconds",
)
@click.option(
    "--highlighting/--no-highlighting",
    default=True,
    help="Enable syntax highlighting for code",
)
@click.option(
    "--remove-tags/--keep-tags", default=True, help="Remove tags after processing"
)
@click.option(
    "--use-conversation-ids/--no-conversation-ids",
    default=True,
    help="Use separate conversation IDs per notebook",
)
def penpal(
    query_tag,
    context_tag,
    kg_tag,
    new_tag,
    subject_tag,
    default_subject,
    use_subject_dirs,
    pre_filter_tag,
    no_pre_filter,
    mcp_tools,
    claude_command,
    poll_interval,
    highlighting,
    remove_tags,
    use_conversation_ids,
):
    """Start the Claude Penpal monitoring service."""

    from inklink.services.claude_penpal_service import ClaudePenpalService

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    # Process MCP tool tags if provided
    mcp_tool_tags = []
    if mcp_tools:
        mcp_tool_tags = [tool.strip() for tool in mcp_tools.split(",")]

    click.echo("Starting Claude Penpal monitoring service")
    click.echo(f"Using Claude command: {claude_command}")
    click.echo("Looking for pages with tags:")
    click.echo(f"  - '{query_tag}' for queries to Claude")
    click.echo(f"  - '{context_tag}' for additional context")
    click.echo(f"  - '{kg_tag}' for Knowledge Graph processing")
    click.echo(f"  - '{new_tag}' to start a new conversation")

    if mcp_tool_tags:
        click.echo(f"Supported MCP tool tags: {', '.join(mcp_tool_tags)}")

    click.echo(
        f"Syntax highlighting for code: {'Enabled' if highlighting else 'Disabled'}"
    )
    click.echo(
        f"Tag removal after processing: {'Enabled' if remove_tags else 'Disabled'}"
    )
    click.echo(
        f"Conversation tracking: {'Per notebook' if use_conversation_ids else 'Simple context'}"
    )

    # Directory structure information
    if use_subject_dirs:
        click.echo(f"Directory structure: Organizing by subject (/{subject_tag}:name/)")
        click.echo(f"Default subject: '{default_subject}'")
    else:
        click.echo("Directory structure: Flat organization (no subjects)")

    # If no_pre_filter flag is set, disable pre-filtering
    actual_pre_filter_tag = None if no_pre_filter else pre_filter_tag

    if no_pre_filter:
        click.echo("Pre-filtering disabled - will check all notebooks")
    else:
        click.echo(
            f"Using pre-filter tag '{pre_filter_tag}' to optimize notebook selection"
        )

    service = ClaudePenpalService(
        claude_command=claude_command,
        query_tag=query_tag,
        context_tag=context_tag,
        knowledge_graph_tag=kg_tag,
        new_conversation_tag=new_tag,
        subject_tag=subject_tag,
        default_subject=default_subject,
        use_subject_dirs=use_subject_dirs,
        pre_filter_tag=actual_pre_filter_tag,
        mcp_tool_tags=mcp_tool_tags,
        poll_interval=poll_interval,
        syntax_highlighting=highlighting,
        remove_tags_after_processing=remove_tags,
        use_conversation_ids=use_conversation_ids,
    )

    service.start_monitoring()

    # Keep running until interrupted
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        click.echo("Stopping service...")
        service.stop_monitoring()
        click.echo("Service stopped")


def main():
    """Entry point for the application."""
    cli()


if __name__ == "__main__":
    main()
