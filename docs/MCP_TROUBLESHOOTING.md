# MCP Server Troubleshooting Guide

This guide covers common issues and solutions when working with MCP (Model Context Protocol) servers in AInTandem.

## Table of Contents

1. [Connection Issues](#connection-issues)
2. [SDK Version Problems](#sdk-version-problems)
3. [Server-Specific Issues](#server-specific-issues)
4. [Configuration Problems](#configuration-problems)
5. [Performance Issues](#performance-issues)

---

## Connection Issues

### Symptom: `Connection timeout after 30s`

**Error Message:**
```
ERROR | [filesystem] Connection timeout after 30s
ERROR | [filesystem] Failed to connect: [filesystem] Connection timeout after 30s
```

**Possible Causes:**

1. **MCP Server not starting** - The server process fails to start
2. **Network/firewall blocking** - Local firewall blocking the connection
3. **Invalid path** - Filesystem server path doesn't exist

**Solutions:**

1. **Verify server can start manually:**
   ```bash
   npx -y @modelcontextprotocol/server-filesystem /path/to/directory
   ```

2. **Check path exists and is accessible:**
   ```bash
   ls -la /path/to/directory
   ```

3. **Increase timeout in config:**
   ```yaml
   mcp_servers:
     - name: "filesystem"
       timeout: 60  # Increase from 30 to 60 seconds
   ```

### Symptom: `BrokenResourceError` or Session Initialization Hangs

**Error Message:**
```
anyio.BrokenResourceError
ExceptionGroup: unhandled errors in a TaskGroup
```

**Root Cause:** MCP Python SDK version 1.9.0+ has known bugs with stdio transport.

**Solution:**

1. **Check current version:**
   ```bash
   pip show mcp
   ```

2. **Downgrade to v1.8.1:**
   ```bash
   pip install mcp==1.8.1
   ```

3. **Verify fix in requirements.txt:**
   ```
   mcp==1.8.1
   ```

**Related Issues:**
- [Issue #1452](https://github.com/modelcontextprotocol/python-sdk/issues/1452) - stdio_client hangs on macOS
- [Issue #1564](https://github.com/modelcontextprotocol/python-sdk/issues/1564) - BrokenResourceError

---

## SDK Version Problems

### Compatible MCP SDK Versions

| Version | Status | Notes |
|---------|--------|-------|
| **1.8.1** | ✅ Stable | Last stable version before bugs introduced |
| 1.9.0 - 1.25.0 | ❌ Broken | Known issues with stdio transport |
| Latest | ⚠️ Unknown | Check GitHub issues for current status |

### Upgrading SDK

Before upgrading MCP SDK, always check:
1. [GitHub Issues](https://github.com/modelcontextprotocol/python-sdk/issues)
2. Release notes for breaking changes
3. Test with a simple connection first

---

## Server-Specific Issues

### Filesystem Server

**Issue:** Permission denied errors

**Solution:**
```yaml
mcp_servers:
  - name: "filesystem"
    args:
      - "-y"
      - "@modelcontextprotocol/server-filesystem"
      - "${AGENT_ROOT_PATH}"  # Ensure path exists and is readable
```

**Issue:** Server exits immediately

**Solution:**
- Verify the path exists: `ls -la /Users/lex.yang/agent-root`
- Check the server isn't receiving EOF on stdin
- Ensure proper async context manager usage

### Web Search (Brave) Server

**Issue:** `BRAVE_API_KEY` not found

**Solution:**
```bash
# Add to .env file
BRAVE_API_KEY=your_api_key_here

# Or set directly in config
mcp_servers:
  - name: "web-search"
    env:
      BRAVE_API_KEY: "your_actual_api_key"
```

**Get API Key:** https://brave.com/search/api/

### GitHub Server

**Issue:** Authentication failures

**Solution:**
```bash
# Set GitHub token with appropriate permissions
export GITHUB_TOKEN=ghp_xxxxxxxxxxxx

# Or in .env
GITHUB_TOKEN=ghp_xxxxxxxxxxxx
```

**Required scopes:** `repo`, `read:org`

### PostgreSQL Server

**Issue:** Connection string format errors

**Correct format:**
```yaml
mcp_servers:
  - name: "postgres"
    args:
      - "mcp-server-postgres"
      - "--connection-string"
      - "postgresql://user:password@host:port/database"
```

**Common mistakes:**
- Missing `postgresql://` prefix
- Wrong port (default is 5432)
- Insufficient permissions

---

## Configuration Problems

### Environment Variable Substitution

**Issue:** Variables not being replaced

**Wrong:**
```yaml
args:
  - "${AGENT_ROOT_PATH}"  # Won't work if not in .env
```

**Correct:**
```bash
# In .env file
AGENT_ROOT_PATH=/Users/lex.yang/agent-root
```

### Command Path Issues

**Issue:** Command not found

**Solution:** Use full paths or ensure command is in PATH

```yaml
# Wrong
command: "./mcp-server"

# Correct
command: "npx"
args: ["-y", "@modelcontextprotocol/server-filesystem", "/path"]
```

---

## Performance Issues

### Slow Tool Loading

**Symptom:** Long delays when loading tools from servers

**Solutions:**

1. **Enable only needed servers:**
   ```yaml
   mcp_servers:
     - name: "filesystem"
       enabled: true
     - name: "github"
       enabled: false  # Disable if not needed
   ```

2. **Reduce health check interval:**
   ```yaml
   health_check:
     enabled: true
     interval: 120  # Check every 2 minutes instead of 60s
   ```

### High Memory Usage

**Causes:**
- Too many tools loaded
- Frequent tool calls
- Not disconnecting unused servers

**Solutions:**

1. **Disconnect unused servers:**
   ```python
   await mcp_bridge.disconnect_server("unused-server")
   ```

2. **Limit tools per agent:**
   ```yaml
   agents:
     - name: "minimal-agent"
       mcp_servers: ["filesystem"]  # Only essential tools
   ```

---

## Debugging Tips

### Enable Debug Logging

```python
# In main.py or your script
import logging
logging.basicConfig(level=logging.DEBUG)
```

### Test Connection Manually

```python
import asyncio
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

async def test_connection():
    params = StdioServerParameters(
        command="npx",
        args=["-y", "@modelcontextprotocol/server-filesystem", "/path"],
    )
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            tools = await session.list_tools()
            print(f"Connected! Found {len(tools.tools)} tools")

asyncio.run(test_connection())
```

### Check Server Process

```bash
# List running MCP servers
ps aux | grep "@modelcontextprotocol/server"

# Kill stuck servers
pkill -9 -f "@modelcontextprotocol/server"
```

---

## Common Error Messages

| Error | Cause | Solution |
|-------|-------|----------|
| `BrokenResourceError` | MCP SDK >= 1.9.0 | Downgrade to v1.8.1 |
| `Connection timeout` | Server not responding | Check server can start manually |
| `Initialization timeout` | Session init hangs | Use `async with ClientSession()` |
| `Permission denied` | File/path permissions | Check directory permissions |
| `API key not found` | Missing env var | Set in .env or config |
| `Command not found` | Wrong command path | Use full path or npx |

---

## Getting Help

If issues persist:

1. **Check logs:** `storage/logs/`
2. **GitHub Issues:** https://github.com/modelcontextprotocol/python-sdk/issues
3. **MCP Documentation:** https://modelcontextprotocol.io
4. **Enable debug mode** and review detailed logs
