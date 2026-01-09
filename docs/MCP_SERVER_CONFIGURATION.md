# MCP Server Configuration Guide

This guide explains how to configure Model Context Protocol (MCP) servers in the AInTandem Agent infrastructure.

## Overview

MCP servers provide tools, resources, and prompts that agents can use. The system supports two transport types:

- **stdio**: Standard input/output (default, for local MCP servers)
- **sse**: Server-Sent Events (for remote/streaming MCP servers)

## Configuration File

MCP server configurations are stored in `config/mcp_servers.yaml`:

```yaml
mcp_servers:
  - name: "server-name"
    description: "Server description"
    transport: "stdio"  # or "sse"
    # ... transport-specific config
    timeout: 30
    enabled: true
    health_check:
      enabled: true
      interval: 60
```

## Transport Types

### Stdio Transport (Default)

Used for local MCP servers that communicate via standard input/output.

```yaml
mcp_servers:
  - name: "filesystem"
    description: "File system access"
    transport: "stdio"
    command: "npx"
    args:
      - "-y"
      - "@modelcontextprotocol/server-filesystem"
      - "${AGENT_ROOT_PATH}"
    env: {}
    timeout: 30
    enabled: true
    health_check:
      enabled: true
      interval: 60
```

**Configuration Fields**:
- `command`: Command to start the MCP server (e.g., `npx`, `uvx`, `node`)
- `args`: List of command arguments
- `env`: Environment variables for the server process
- `timeout`: Request timeout in seconds

### SSE Transport

Used for remote MCP servers or servers that support streaming responses.

```yaml
mcp_servers:
  - name: "remote-mcp-server"
    description: "Remote MCP server with streaming support"
    transport: "sse"
    sse:
      url: "https://example.com/mcp/sse"
      headers:
        Authorization: "Bearer ${MCP_SERVER_TOKEN}"
        X-Custom-Header: "value"
    timeout: 30
    enabled: false
    health_check:
      enabled: true
      interval: 60
```

**Configuration Fields**:
- `sse.url`: SSE endpoint URL
- `sse.headers`: HTTP headers for requests
- `timeout`: Request timeout in seconds

**Note**: SSE transport supports streaming tool execution via the `/sse/tools/call` API endpoint.

## Available MCP Servers

### Official MCP Servers

#### Filesystem

Provides file system read/write access.

```yaml
- name: "filesystem"
  description: "File system read/write access"
  transport: "stdio"
  command: "npx"
  args:
    - "-y"
    - "@modelcontextprotocol/server-filesystem"
    - "${AGENT_ROOT_PATH}"
  env: {}
  timeout: 30
  enabled: true
```

**Tools**: `read_file`, `write_file`, `create_directory`, `list_directory`, `move_file`, `search_files`

**Requirements**: Set `AGENT_ROOT_PATH` in `.env` to the allowed directory path.

#### Brave Search

Web search using Brave Search API.

```yaml
- name: "web-search"
  description: "Web search via Brave Search API"
  transport: "stdio"
  command: "npx"
  args:
    - "-y"
    - "@modelcontextprotocol/server-brave-search"
  env:
    BRAVE_API_KEY: "${BRAVE_API_KEY}"
  timeout: 30
  enabled: true
```

**Tools**: `brave_web_search`

**Requirements**: Set `BRAVE_API_KEY` in `.env`. Get API key from [Brave Search](https://brave.com/search/api/).

#### GitHub

GitHub repository and operations integration.

```yaml
- name: "github"
  description: "GitHub operations"
  transport: "stdio"
  command: "uvx"
  args:
    - "mcp-server-github"
  env:
    GITHUB_TOKEN: "${GITHUB_TOKEN}"
  timeout: 30
  enabled: true
```

**Tools**: `create_issue`, `create_pull_request`, `fork_repository`, `push_files`, etc.

**Requirements**: Set `GITHUB_TOKEN` in `.env`. Create token with `repo` scope at [GitHub Settings](https://github.com/settings/tokens).

#### PostgreSQL

PostgreSQL database operations.

```yaml
- name: "postgres"
  description: "PostgreSQL database access"
  transport: "stdio"
  command: "uvx"
  args:
    - "mcp-server-postgres"
    - "--connection-string"
    - "${DATABASE_URL}"
  env: {}
  timeout: 30
  enabled: true
```

**Tools**: `query`, `execute_sql`, `get_tables`, `get_table_info`

**Requirements**: Set `DATABASE_URL` in `.env` (e.g., `postgresql://user:password@host:port/database`).

#### Google Maps

Google Maps services integration.

```yaml
- name: "google-maps"
  description: "Google Maps services"
  transport: "stdio"
  command: "npx"
  args:
    - "-y"
    - "@modelcontextprotocol/server-google-maps"
  env:
    GOOGLE_MAPS_API_KEY: "${GOOGLE_MAPS_API_KEY}"
  timeout: 30
  enabled: true
```

**Tools**: `maps_geocode`, `maps_search`, `maps_directions`, `maps_places`

**Requirements**: Set `GOOGLE_MAPS_API_KEY` in `.env`. Get key from [Google Cloud Console](https://console.cloud.google.com/).

#### Puppeteer

Web automation and scraping.

```yaml
- name: "puppeteer"
  description: "Web automation with Puppeteer"
  transport: "stdio"
  command: "npx"
  args:
    - "-y"
    - "@modelcontextprotocol/server-puppeteer"
  env: {}
  timeout: 60
  enabled: true
  health_check:
    enabled: false  # Puppeteer starts slowly
```

**Tools**: `puppeteer_navigate`, `puppeteer_screenshot`, `puppeteer_click`, `puppeteer_fill`, `puppeteer_select`

**Note**: Puppeteer requires more time to start. Consider disabling health check.

## Environment Variables

MCP server configurations support environment variable substitution using `${VAR_NAME}` syntax:

```yaml
env:
  API_KEY: "${MY_API_KEY}"      # Required, will error if missing
  OPTIONAL_VAR: "${OPTIONAL_VAR:-default}"  # Optional with default
```

Set variables in `.env`:

```bash
# MCP Server Credentials
BRAVE_API_KEY=your_brave_api_key
GITHUB_TOKEN=your_github_token
GOOGLE_MAPS_API_KEY=your_google_maps_key
DATABASE_URL=postgresql://user:password@localhost:5432/db

# Paths
AGENT_ROOT_PATH=/path/to/allowed/directory
```

## Agent Integration

Assign MCP servers to agents in `config/agents.yaml`:

```yaml
agents:
  - name: "developer"
    role: "Code Assistant"
    mcp_servers: ["filesystem", "github"]  # Servers this agent can use
    llm_model: "gpt-4"
    enabled: true
```

## Health Checks

MCP servers can have health check configurations:

```yaml
health_check:
  enabled: true    # Enable/disable health checks
  interval: 60     # Check interval in seconds
```

The system will periodically ping connected servers and log warnings if a server becomes unresponsive.

## Troubleshooting

### Connection Issues

If an MCP server fails to connect:

1. **Check the command**: Ensure the command (`npx`, `uvx`, etc.) is installed and accessible
2. **Verify arguments**: Check that all arguments are correct
3. **Environment variables**: Ensure all required env vars are set in `.env`
4. **Timeout**: Increase `timeout` value if the server takes longer to start

### SDK Version Issues

The MCP SDK has known issues with version 1.9.0+. Ensure you're using `mcp==1.8.1`:

```bash
pip install mcp==1.8.1
```

See [docs/MCP_TROUBLESHOOTING.md](MCP_TROUBLESHOOTING.md) for more details.

### Server-Specific Issues

- **Puppeteer**: May require additional dependencies. Install Chromium:
  ```bash
  # macOS
  brew install chromium

  # Linux
  sudo apt-get install chromium-browser
  ```

- **PostgreSQL**: Ensure the database is accessible and credentials are correct:
  ```bash
  psql "${DATABASE_URL}" -c "SELECT 1"
  ```

## API Usage

### List Available Tools

```bash
curl http://localhost:8000/sse/tools
```

Returns all tools with streaming support information.

### List Connected Servers

```bash
curl http://localhost:8000/sse/servers
```

Returns server status including transport type.

### Streaming Tool Call (SSE only)

```bash
curl -N -X POST http://localhost:8000/sse/tools/call \
  -H "Content-Type: application/json" \
  -d '{
    "server_name": "remote-mcp-server",
    "tool_name": "stream_tool",
    "arguments": {"query": "..."}
  }'
```

## Advanced Configuration

### Custom MCP Servers

You can add custom MCP servers by specifying the command:

```yaml
- name: "custom-server"
  description: "Custom MCP server"
  transport: "stdio"
  command: "node"
  args: ["/path/to/custom-mcp-server.js"]
  env:
    CUSTOM_CONFIG: "${CUSTOM_CONFIG_PATH}"
  timeout: 30
  enabled: true
```

### Remote SSE Servers

For remote MCP servers that support SSE:

```yaml
- name: "remote-sse-server"
  description: "Remote SSE MCP server"
  transport: "sse"
  sse:
    url: "https://api.example.com/mcp/sse"
    headers:
      Authorization: "Bearer ${API_KEY}"
      X-API-Version: "v1"
  timeout: 60
  enabled: true
```

### Multiple Instances

Run multiple instances of the same server type:

```yaml
- name: "filesystem-work"
  description: "Work directory access"
  transport: "stdio"
  command: "npx"
  args: ["-y", "@modelcontextprotocol/server-filesystem", "/work"]
  enabled: true

- name: "filesystem-home"
  description: "Home directory access"
  transport: "stdio"
  command: "npx"
  args: ["-y", "@modelcontextprotocol/server-filesystem", "/home"]
  enabled: true
```

## Best Practices

1. **Security**: Use environment variables for sensitive data (API keys, tokens)
2. **Timeouts**: Set appropriate timeouts based on server response time
3. **Health Checks**: Enable health checks for critical servers
4. **Isolation**: Use separate servers for different access levels (e.g., read-only vs read-write)
5. **Documentation**: Add clear descriptions for custom servers
6. **Testing**: Test server connections before enabling in production

## References

- [MCP Specification](https://modelcontextprotocol.io/)
- [Official MCP Servers](https://github.com/modelcontextprotocol)
- [Troubleshooting Guide](MCP_TROUBLESHOOTING.md)
