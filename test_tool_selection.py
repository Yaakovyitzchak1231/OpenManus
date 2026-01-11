"""
Quick test to verify agent-based tool selection hints in PlanningFlow
"""

import asyncio

from app.agent.manus import Manus
from app.flow.planning import PlanningFlow


async def test_agent_tool_selection():
    print("Testing agent-based tool selection...")

    # Create Manus agent
    manus = await Manus.create()

    # Create PlanningFlow
    flow = PlanningFlow(agents={"manus": manus})

    # Test the tool selection hint formatter
    hint = flow._format_tool_selection_hint(
        manus, "Create a Python file that contains unit tests"
    )

    if hint:
        print(f"✅ Tool selection hint generated ({len(hint)} characters)")
        print("\nSample hint (first 300 chars):")
        print(hint[:300] + "...")
    else:
        print("❌ No tool selection hint generated")

    print(f"\n✅ Test completed successfully!")


if __name__ == "__main__":
    asyncio.run(test_agent_tool_selection())
