"""
Test actual MCP tool execution - call filesystem tools
"""

import asyncio

from app.agent.manus import Manus


async def test_real_mcp_call():
    print("=" * 70)
    print("TESTING ACTUAL MCP TOOL EXECUTION")
    print("=" * 70)

    # Create agent with MCP
    print("\n1. Creating Manus agent with MCP servers...")
    manus = await Manus.create()

    # List available tools
    mcp_tools = [
        t
        for t in manus.available_tools.tools
        if hasattr(t, "server_id") and t.server_id
    ]
    print(f"\n2. MCP tools available: {len(mcp_tools)}")
    for tool in mcp_tools:
        print(f"   - {tool.name}")

    if not mcp_tools:
        print("\n❌ No MCP tools available - cannot test execution")
        await manus.cleanup()
        return False

    # Try to execute a filesystem tool (read_file or list_directory)
    print("\n3. Attempting to call MCP filesystem tool...")

    # Find a list or read tool
    list_tool = None
    for tool in mcp_tools:
        if "list" in tool.name.lower() or "dir" in tool.name.lower():
            list_tool = tool
            break

    if list_tool:
        print(f"   Using tool: {list_tool.name}")
        try:
            # Try to list workspace directory
            workspace = (
                "c:/Users/jacob/OneDrive/Desktop/OpenManus_Antigravity/openmanus"
            )
            result = await list_tool.execute(path=workspace)

            if result.error:
                print(f"\n❌ Tool execution error: {result.error}")
                success = False
            else:
                print(f"\n✅ SUCCESS! MCP tool executed successfully!")
                print(
                    f"   Output preview: {result.output[:200] if result.output else 'No output'}..."
                )
                success = True
        except Exception as e:
            print(f"\n❌ Exception during tool execution: {e}")
            success = False
    else:
        print("\n⚠️  Could not find a list/directory tool to test")
        success = False

    # Cleanup
    await manus.cleanup()

    print("\n" + "=" * 70)
    return success


if __name__ == "__main__":
    result = asyncio.run(test_real_mcp_call())
    exit(0 if result else 1)
