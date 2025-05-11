# GitHub MCP Integration

This document outlines how the Remarkable Ink Link project integrates with GitHub's MCP (Model Context Protocol) server for enhanced development workflows.

## Setup

The GitHub MCP server has been configured to run with Docker:

```bash
# The server can be started with:
docker run -i --rm -e GITHUB_PERSONAL_ACCESS_TOKEN=$GITHUB_PAT ghcr.io/github/github-mcp-server
```

## Configuration

A configuration file has been created at `~/.claude/mcp/config.json`:

```json
{
  "mcpServers": {
    "github": {
      "command": "docker",
      "args": [
        "run", "-i", "--rm", "-e", "GITHUB_PERSONAL_ACCESS_TOKEN",
        "ghcr.io/github/github-mcp-server"
      ],
      "env": {
        "GITHUB_PERSONAL_ACCESS_TOKEN": "[YOUR_PAT_HERE]"
      }
    }
  }
}
```

Replace `[YOUR_PAT_HERE]` with your GitHub Personal Access Token.

## Available Tools

The GitHub MCP server provides the following toolsets:

- `repos`: Repository management
- `issues`: Issue tracking
- `pull_requests`: PR workflows
- `discussions`: GitHub Discussions

## Usage with Claude

When working with Claude, you can use the GitHub MCP server to:

1. Query repository information
2. Create and manage issues
3. Review and manage pull requests
4. Access GitHub Discussions

## Security Notes

- Never commit your GitHub PAT to version control
- Store your PAT in environment variables or secure credential storage
- Consider using GitHub Apps for production deployments instead of PATs