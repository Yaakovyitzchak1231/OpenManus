"""
Test MCP server connection and tool discovery logging
"""

import asyncio

from app.agent.manus import Manus


async def test_mcp_connection():
    print("=" * 60)
    print("TESTING MCP SERVER CONNECTION AND TOOL DISCOVERY")
    print("=" * 60)

    print("\n1. Creating Manus agent (this triggers MCP initialization)...")
    manus = await Manus.create()

    print(f"\n2. Connected MCP servers: {list(manus.connected_servers.keys())}")

    print(f"\n3. Total tools available: {len(manus.available_tools.tools)}")

    print("\n4. Tool breakdown:")
    # Separate MCP tools from built-in tools
    mcp_tools = []
    builtin_tools = []

    for tool in manus.available_tools.tools:
        if hasattr(tool, "server_id") and tool.server_id:
            mcp_tools.append(tool)
        else:
            builtin_tools.append(tool)

    print(f"   - Built-in tools: {len(builtin_tools)}")
    for tool in builtin_tools:
        print(f"     • {tool.name}")

    if mcp_tools:
        print(f"\n   - MCP tools: {len(mcp_tools)}")
        for tool in mcp_tools:
            server_id = getattr(tool, "server_id", "unknown")
            desc = (
                tool.description[:60] + "..."
                if len(tool.description) > 60
                else tool.description
            )
            print(f"     • {tool.name} (from {server_id}): {desc}")
    else:
        print(f"\n   - MCP tools: 0")
        print(
            "     ⚠️  No MCP tools discovered. Check MCP server connection logs above."
        )

    print("\n" + "=" * 60)
    print("TEST COMPLETE")
    print("=" * 60)

    # Cleanup
    await manus.cleanup()


if __name__ == "__main__":
    asyncio.run(test_mcp_connection())
