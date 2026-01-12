"""
Quick test to verify MCP tools are discovered
"""

import asyncio

from app.agent.manus import Manus


async def main():
    print("=" * 60)
    print("QUICK MCP VERIFICATION TEST")
    print("=" * 60)

    # Create Manus agent (properly initialized with MCP)
    manus = await Manus.create()

    # Count tools by type
    built_in = []
    mcp_tools = []

    for tool in manus.available_tools.tools:
        if hasattr(tool, "server_id") and tool.server_id:
            mcp_tools.append(tool)
        else:
            built_in.append(tool)

    print(f"\n✅ Built-in tools: {len(built_in)}")
    for tool in built_in:
        print(f"   - {tool.name}")

    print(f"\n📦 MCP tools discovered: {len(mcp_tools)}")
    if mcp_tools:
        print("   SUCCESS! MCP tools are working:")
        for tool in mcp_tools:
            print(f"   - {tool.name} (from {tool.server_id})")
    else:
        print("   ❌ No MCP tools found. Check logs above for errors.")

    print("\n" + "=" * 60)

    # Cleanup
    await manus.cleanup()

    return len(mcp_tools)


if __name__ == "__main__":
    count = asyncio.run(main())
    exit(0 if count > 0 else 1)
