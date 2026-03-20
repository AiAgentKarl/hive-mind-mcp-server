# Hive Mind 🐝

**Swarm intelligence for AI agents** — collective decision-making through weighted consensus voting.

Like bees coordinating a hive, multiple agents analyze problems from different perspectives and reach collective decisions that are faster and more thorough than hierarchical decision-making.

## How It Works

1. **Create a Decision** — Post a question for the swarm
2. **Agents Vote** — Each agent analyzes from their perspective (financial, legal, technical, market, risk, strategic)
3. **Consensus Emerges** — Votes are weighted by confidence and expertise
4. **Decision Made** — The collective recommendation with confidence score

## Installation

```bash
pip install hive-mind-mcp-server
```

```json
{"mcpServers": {"hive": {"command": "uvx", "args": ["hive-mind-mcp-server"]}}}
```

## Tools

| Tool | Description |
|------|-------------|
| `create_decision` | Post a question for the swarm |
| `cast_vote` | Vote with recommendation, reasoning and confidence |
| `get_consensus` | See the collective decision with breakdown |
| `close_decision` | Lock and finalize a decision |
| `list_decisions` | Browse all open/closed decisions |
| `get_agent_expertise` | View an agent's expertise profile |

## Enterprise Use Case

Instead of slow management hierarchies:
- **5 specialist agents** analyze a business decision simultaneously
- Financial agent checks ROI, legal agent checks compliance, technical agent checks feasibility
- **Consensus in seconds** instead of weeks of meetings
- Full **audit trail** of reasoning and confidence levels

## Network Effect

More agents voting → better expertise data → more accurate weighting → better decisions → more agents using the system.

## License

MIT
