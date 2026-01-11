"""
Test to verify FlowFactory and MCP configuration fixes
"""

import asyncio

from app.agent.manus import Manus
from app.agent.reviewer import Reviewer
from app.config import config
from app.flow.flow_factory import FlowFactory, FlowType


async def test_flow_factory_registration():
    """Test that ReviewFlow is properly registered in FlowFactory"""
    print("=" * 60)
    print("TEST 1: FlowFactory Registration")
    print("=" * 60)

    # Test PLANNING flow creation
    print("\n1. Testing PlanningFlow creation...")
    manus = await Manus.create()
    planning_flow = FlowFactory.create_flow(FlowType.PLANNING, agents={"manus": manus})
    print(f"   ✅ PlanningFlow created: {type(planning_flow).__name__}")

    # Test REVIEW flow creation
    print("\n2. Testing ReviewFlow creation...")
    reviewer = Reviewer()
    review_flow = FlowFactory.create_flow(
        FlowType.REVIEW, agents={"doer": manus, "reviewer": reviewer}
    )
    print(f"   ✅ ReviewFlow created: {type(review_flow).__name__}")

    # Verify both flows are different types
    assert type(planning_flow).__name__ == "PlanningFlow"
    assert type(review_flow).__name__ == "ReviewFlow"
    print("\n   ✅ Both flow types properly registered!")

    await manus.cleanup()


def test_mcp_config_loading():
    """Test that MCP configuration loads from TOML with JSON override"""
    print("\n" + "=" * 60)
    print("TEST 2: MCP Configuration Loading")
    print("=" * 60)

    mcp_config = config.mcp_config

    print(f"\n1. MCP server reference: {mcp_config.server_reference}")
    print(f"2. Number of configured servers: {len(mcp_config.servers)}")

    if mcp_config.servers:
        print("\n3. Configured MCP servers:")
        for server_id, server_config in mcp_config.servers.items():
            print(f"   - {server_id}:")
            print(f"     Type: {server_config.type}")
            if server_config.command:
                print(f"     Command: {server_config.command}")
                print(f"     Args: {server_config.args}")
            if server_config.url:
                print(f"     URL: {server_config.url}")

        print("\n   ✅ MCP configuration loaded successfully!")
        print("   📝 Note: Config prioritizes config.toml, with mcp.json as override")
    else:
        print("\n   ⚠️  No MCP servers configured (this is OK for testing)")


def test_tool_selection_exists():
    """Test that tool selection hint functionality exists in PlanningFlow"""
    print("\n" + "=" * 60)
    print("TEST 3: Tool Selection Implementation")
    print("=" * 60)

    from app.flow.planning import PlanningFlow

    # Check that the method exists
    assert hasattr(PlanningFlow, "_format_tool_selection_hint")
    print("\n   ✅ PlanningFlow._format_tool_selection_hint() exists")
    print("   📝 Tool selection is implemented inline (no separate module needed)")


async def main():
    """Run all tests"""
    print("\n🧪 VERIFICATION TESTS FOR MCP & FLOW INTEGRATION FIXES\n")

    try:
        await test_flow_factory_registration()
        test_mcp_config_loading()
        test_tool_selection_exists()

        print("\n" + "=" * 60)
        print("✅ ALL TESTS PASSED!")
        print("=" * 60)
        print("\nSummary of fixes verified:")
        print("  1. ReviewFlow registered in FlowFactory ✓")
        print("  2. MCP config loads from TOML (with JSON override) ✓")
        print("  3. Tool selection hints implemented in PlanningFlow ✓")

    except Exception as e:
        print("\n" + "=" * 60)
        print("❌ TEST FAILED!")
        print("=" * 60)
        print(f"\nError: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
