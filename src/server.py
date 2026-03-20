"""Hive Mind MCP Server — Schwarm-Intelligenz für KI-Agenten."""

from mcp.server.fastmcp import FastMCP
from src.tools.hive_tools import register_hive_tools

mcp = FastMCP(
    "Hive Mind",
    instructions=(
        "Swarm intelligence for AI agents. Like bees coordinating a hive, "
        "multiple agents analyze problems from different perspectives "
        "(financial, legal, technical, market, risk) and reach collective "
        "decisions through weighted consensus voting. Faster and more "
        "thorough than hierarchical decision-making."
    ),
)

register_hive_tools(mcp)


def main():
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
