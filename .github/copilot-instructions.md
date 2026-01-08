# GitHub Copilot Instructions for OpenManus

This repo implements general-purpose and MCP-driven agents with pluggable tools, configurable LLM backends, and optional multi-agent planning. Use these notes to quickly navigate architecture and follow project conventions.

## Architecture Overview
- **Agents:** `Manus`, `MCPAgent`, and tasks like data analysis extend [app/agent/base.py](app/agent/base.py) via `ToolCallAgent` ([app/agent/toolcall.py](app/agent/toolcall.py)). Agents maintain `memory`, run a `think() → act() → run()` loop, and finish on special tools (e.g., `terminate`).
- **Tools:** Local tools are grouped via `ToolCollection` (e.g., Python, Browser, Editor, AskHuman, Terminate). MCP tools are discovered dynamically from connected servers. See [app/tool](app/tool) and MCP client in [app/tool/mcp.py](app/tool/mcp.py).
- **Flows:** Multi-agent orchestration uses `PlanningFlow` ([app/flow/planning.py](app/flow/planning.py)) created by `FlowFactory` ([app/flow/flow_factory.py](app/flow/flow_factory.py)). `PlanningFlow` builds a plan via `PlanningTool`, marks step status, and delegates steps to agents.
- **LLM:** [app/llm.py](app/llm.py) abstracts OpenAI/Azure/AWS Bedrock, supports `ask`, `ask_tool`, `ask_with_images`, tracks token usage (`max_input_tokens`, streaming/non-streaming) and handles retries.
- **Config:** Centralized in [app/config.py](app/config.py), loaded from `config/config.toml`. Keys: `llm`, `browser`, `search`, `sandbox`, `daytona`, `mcp`, `runflow`. MCP server refs are loaded from `config/mcp.json` if present.
- **MCP Server:** [app/mcp/server.py](app/mcp/server.py) exposes `bash`, `browser`, `editor`, `terminate` via FastMCP; run via [run_mcp_server.py](run_mcp_server.py).

## Developer Workflows
- **Default agent:**
  ```bash
  python main.py
  # or
  python main.py --prompt "Build a simple TODO app"
  ```
- **MCP agent + server:**
  ```bash
  python run_mcp_server.py           # start MCP tools (stdio)
  python run_mcp.py -c stdio -i      # interactive agent using MCP tools
  python run_mcp.py -c stdio -p "Search docs and summarize"
  ```
- **Multi-agent planning:**
  ```bash
  # Enable data analysis agent in config/config.toml
  # [runflow]\nuse_data_analysis_agent = true
  python run_flow.py
  ```
- **Optional integrations:**
  - Daytona sandbox: see [app/daytona/README.md](app/daytona/README.md) and run `python sandbox_main.py`.
  - A2A protocol: see [protocol/a2a/app/README.md](protocol/a2a/app/README.md); run `python -m protocol.a2a.app.main`.
  - Chart visualization: see [app/tool/chart_visualization/README.md](app/tool/chart_visualization/README.md); npm install then Python tests.

## Project Conventions
- **Agent prompts:** `system_prompt` and `next_step_prompt` live in [app/prompt/**](app/prompt). `Manus` adjusts `next_step_prompt` using browser context when recent tool calls include the browser.
- **Tool call pattern:** Agents call `LLM.ask_tool(...)` with `ToolCollection.to_params()`. Assistant messages include `tool_calls`; tool results are stored as `Message.tool_message(...)` with `tool_call_id`.
- **Planning steps:** Use concise steps; optionally tag executors in brackets, e.g., `[data_analysis] Summarize CSV before charting`. `PlanningFlow` marks step statuses and summarizes at completion.
- **Termination:** Any tool in `special_tool_names` (default includes `terminate`) sets `AgentState.FINISHED`.
- **Workspace outputs:** Agents and tools read/write under `workspace/` (e.g., visualization outputs).

## Extending the Codebase
- **Add a tool:** Implement `BaseTool` in [app/tool](app/tool), define `to_param()` schema, ensure `execute()` returns serializable results. Register in `Manus.available_tools` or via MCP server `register_tool()`.
- **Create an agent:** Subclass `ToolCallAgent`, set `name`, `system_prompt`, `available_tools`, and any `special_tool_names`. For MCP-backed agents, use `MCPClients` to connect and refresh tools.
- **Add a flow:** Implement `BaseFlow.execute()` in [app/flow/base.py](app/flow/base.py) and map a new `FlowType` in [app/flow/flow_factory.py](app/flow/flow_factory.py).

## Gotchas / Tips
- **Tokens:** `TokenLimitExceeded` may surface from `LLM`; reduce context or disable streaming.
- **Config:** Ensure `config/config.toml` exists; example files in `config/` help bootstrap providers and features.
- **Windows:** Activate venv via `.venv\Scripts\activate`; `playwright install` if browser tooling is needed.

If any workflow or pattern above is unclear or missing, tell me which part to elaborate (e.g., MCP config shape, planning tool schema, or chart visualization run steps).
