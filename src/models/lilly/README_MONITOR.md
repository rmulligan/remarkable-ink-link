# Lilly Monitor Service

The Lilly Monitor Service watches for reMarkable notebooks tagged with 'Lilly' and processes them using Claude's vision capabilities. When a tagged notebook or page is detected, the service:

1. Downloads the notebook from reMarkable Cloud
2. Extracts the pages and renders them as PNG images
3. Processes each page with Claude's vision capabilities
4. Saves the responses as text files and appends them to the original notebook
5. Updates the knowledge graph with entities and relationships extracted from the content
6. Removes the 'Lilly' tag after successful processing

## Usage

### Starting the Monitor

To start the Lilly Monitor service, run:

```bash
./start_monitor.sh
```

By default, this will:
- Monitor for notebooks tagged with 'Lilly'
- Check for new content every 60 seconds
- Use the standard 'claude' command to process images
- Save processing logs to the `logs/` directory

### Command Line Options

You can customize the monitor with the following options:

```bash
./start_monitor.sh --tag=CustomTag --interval=30 --claude-command="claude --persona=researcher" --once
```

- `--tag=<tag>`: The tag to search for (default: "Lilly")
- `--interval=<seconds>`: How often to check for tagged notebooks (default: 60)
- `--claude-command=<cmd>`: The command to run Claude (default: "claude")
- `--once`: Run once and exit, rather than running continuously

### Testing the Monitor

To quickly test if the monitor is working correctly:

1. Tag a notebook or page on your reMarkable tablet with 'Lilly'
2. Run the monitor with the `--once` flag:
   ```bash
   ./start_monitor.sh --once
   ```
3. The monitor should detect and process the tagged content

## Integration with Lilly Workspace

The monitor is fully integrated with the Lilly workspace and leverages:

1. **Knowledge Graph**: Updates the Neo4j "lilly_knowledge" database with extracted entities and relationships
2. **Vision Capabilities**: Uses Claude's vision capabilities to interpret handwritten content
3. **Workspace Structure**: Saves processed content in the Lilly workspace for future reference

## Workflow

The typical workflow for using the Lilly Monitor service is:

1. **Tag Content**: Write notes in your reMarkable tablet and tag them with 'Lilly'
2. **Automatic Processing**: The monitor detects the tag, processes the content, and appends the response
3. **Return to reMarkable**: View Claude's responses directly in your reMarkable notebook
4. **Knowledge Integration**: All content and relationships are stored in the knowledge graph

## Troubleshooting

If you encounter issues with the monitor service:

- Check the logs in the `logs/` directory for error messages
- Verify that the 'claude' command is working correctly
- Ensure your reMarkable Cloud credentials are valid and accessible
- Check that the 'rmapi' tool is properly installed and configured

## Advanced Configuration

For more advanced configuration options, you can edit the `config.py` file in the main inklink project. Relevant settings include:

- `RMAPI_PATH`: Path to the rmapi executable
- `TEMP_DIR`: Directory for temporary files
- `OUTPUT_DIR`: Directory for output files

You can also create a `.env` file in the project root to override these settings.

## Technical Details

The Lilly Monitor Service is an extension of the existing CassidyMonitor with these modifications:

1. Uses Claude's vision capabilities rather than the `-c` code option
2. Integrates with the Lilly knowledge graph and workspace
3. Saves responses as Markdown files for better formatting
4. Uses custom prompts designed for handwritten content analysis