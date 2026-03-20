"""Hive-Mind-Tools — Schwarm-Intelligenz und kollektive Entscheidungsfindung."""

import json
import sqlite3
import hashlib
from datetime import datetime
from pathlib import Path
from mcp.server.fastmcp import FastMCP

DB_PATH = Path.home() / ".hive-mind" / "hive.db"


def _get_db():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("""
        CREATE TABLE IF NOT EXISTS decisions (
            id TEXT PRIMARY KEY,
            question TEXT NOT NULL,
            context TEXT DEFAULT '',
            status TEXT DEFAULT 'open',
            created_by TEXT DEFAULT '',
            created_at TEXT NOT NULL,
            closed_at TEXT DEFAULT '',
            final_decision TEXT DEFAULT '',
            confidence REAL DEFAULT 0.0
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS votes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            decision_id TEXT NOT NULL,
            agent_id TEXT NOT NULL,
            perspective TEXT DEFAULT '',
            recommendation TEXT NOT NULL,
            reasoning TEXT DEFAULT '',
            confidence REAL DEFAULT 0.5,
            expertise_area TEXT DEFAULT '',
            voted_at TEXT NOT NULL,
            FOREIGN KEY (decision_id) REFERENCES decisions(id),
            UNIQUE(decision_id, agent_id)
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS agent_expertise (
            agent_id TEXT NOT NULL,
            area TEXT NOT NULL,
            score REAL DEFAULT 0.5,
            total_votes INTEGER DEFAULT 0,
            correct_votes INTEGER DEFAULT 0,
            updated_at TEXT NOT NULL,
            PRIMARY KEY (agent_id, area)
        )
    """)
    conn.commit()
    return conn


def register_hive_tools(mcp: FastMCP):

    @mcp.tool()
    async def create_decision(
        question: str,
        context: str = "",
        decision_id: str = "",
        created_by: str = "",
    ) -> dict:
        """Create a new decision for the swarm to evaluate.

        Multiple agents can then vote on this decision from different
        perspectives (financial, legal, technical, market, risk).
        The hive mind aggregates votes into a collective decision.

        Args:
            question: The decision question (e.g. "Should we launch product X?")
            context: Background information for the decision
            decision_id: Custom ID (auto-generated if empty)
            created_by: Who initiated the decision
        """
        conn = _get_db()

        if not decision_id:
            # Kurze ID aus Question-Hash
            decision_id = hashlib.md5(
                f"{question}{datetime.utcnow().isoformat()}".encode()
            ).hexdigest()[:12]

        conn.execute("""
            INSERT INTO decisions (id, question, context, status, created_by, created_at)
            VALUES (?, ?, ?, 'open', ?, ?)
        """, (decision_id, question, context, created_by, datetime.utcnow().isoformat()))
        conn.commit()

        return {
            "status": "created",
            "decision_id": decision_id,
            "question": question,
            "message": "Decision created. Agents can now vote using cast_vote.",
            "perspectives_needed": [
                "financial", "technical", "legal", "market", "risk", "strategic"
            ],
        }

    @mcp.tool()
    async def cast_vote(
        decision_id: str,
        agent_id: str,
        recommendation: str,
        reasoning: str = "",
        confidence: float = 0.5,
        perspective: str = "",
        expertise_area: str = "",
    ) -> dict:
        """Cast a vote on an open decision.

        Each agent votes from their perspective with a recommendation,
        reasoning and confidence level. Votes are weighted by expertise.

        Args:
            decision_id: The decision to vote on
            agent_id: Your agent identifier
            recommendation: Your recommendation (e.g. "approve", "reject", "modify", or free text)
            reasoning: Why you recommend this (1-3 sentences)
            confidence: How confident you are (0.0 to 1.0)
            perspective: Your analysis angle (financial, technical, legal, market, risk, strategic)
            expertise_area: Your area of expertise for weighting
        """
        conn = _get_db()

        # Decision prüfen
        decision = conn.execute(
            "SELECT * FROM decisions WHERE id = ?", (decision_id,)
        ).fetchone()
        if not decision:
            return {"error": f"Decision '{decision_id}' not found"}
        if decision["status"] != "open":
            return {"error": "Decision is already closed"}

        # Vote speichern (überschreibt vorherigen Vote des gleichen Agents)
        conn.execute("""
            INSERT OR REPLACE INTO votes
            (decision_id, agent_id, perspective, recommendation, reasoning,
             confidence, expertise_area, voted_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (decision_id, agent_id, perspective, recommendation, reasoning,
              min(max(confidence, 0.0), 1.0), expertise_area,
              datetime.utcnow().isoformat()))

        # Expertise-Score aktualisieren
        if expertise_area:
            conn.execute("""
                INSERT INTO agent_expertise (agent_id, area, score, total_votes, updated_at)
                VALUES (?, ?, 0.5, 1, ?)
                ON CONFLICT(agent_id, area) DO UPDATE SET
                    total_votes = total_votes + 1,
                    updated_at = ?
            """, (agent_id, expertise_area, datetime.utcnow().isoformat(),
                  datetime.utcnow().isoformat()))

        conn.commit()

        vote_count = conn.execute(
            "SELECT COUNT(*) FROM votes WHERE decision_id = ?", (decision_id,)
        ).fetchone()[0]

        return {
            "status": "voted",
            "decision_id": decision_id,
            "agent": agent_id,
            "recommendation": recommendation,
            "total_votes": vote_count,
        }

    @mcp.tool()
    async def get_consensus(decision_id: str) -> dict:
        """Get the current consensus status for a decision.

        Aggregates all votes, weights by expertise and confidence,
        and produces a collective decision with confidence score.

        Args:
            decision_id: The decision to analyze
        """
        conn = _get_db()

        decision = conn.execute(
            "SELECT * FROM decisions WHERE id = ?", (decision_id,)
        ).fetchone()
        if not decision:
            return {"error": f"Decision '{decision_id}' not found"}

        votes = conn.execute("""
            SELECT v.*, COALESCE(e.score, 0.5) as expertise_score
            FROM votes v
            LEFT JOIN agent_expertise e ON v.agent_id = e.agent_id AND v.expertise_area = e.area
            WHERE v.decision_id = ?
            ORDER BY v.voted_at
        """, (decision_id,)).fetchall()

        if not votes:
            return {
                "decision_id": decision_id,
                "question": decision["question"],
                "status": "no_votes",
                "message": "No votes cast yet.",
            }

        # Votes nach Recommendation gruppieren und gewichten
        recommendation_scores = {}
        total_weight = 0
        perspectives_covered = set()

        for v in votes:
            rec = v["recommendation"].lower().strip()
            # Gewicht = Konfidenz * Expertise-Score
            weight = v["confidence"] * (0.5 + v["expertise_score"])
            recommendation_scores[rec] = recommendation_scores.get(rec, 0) + weight
            total_weight += weight
            if v["perspective"]:
                perspectives_covered.add(v["perspective"])

        # Normalisierte Scores berechnen
        normalized = {}
        for rec, score in recommendation_scores.items():
            normalized[rec] = round(score / total_weight * 100, 1) if total_weight > 0 else 0

        # Gewinner bestimmen
        winner = max(recommendation_scores, key=recommendation_scores.get)
        winner_pct = normalized[winner]

        # Konsens-Stärke bewerten
        if winner_pct >= 80:
            consensus_strength = "strong"
        elif winner_pct >= 60:
            consensus_strength = "moderate"
        elif winner_pct >= 40:
            consensus_strength = "weak"
        else:
            consensus_strength = "no_consensus"

        # Detaillierte Votes
        vote_details = []
        for v in votes:
            vote_details.append({
                "agent": v["agent_id"],
                "perspective": v["perspective"],
                "recommendation": v["recommendation"],
                "reasoning": v["reasoning"],
                "confidence": v["confidence"],
                "expertise_score": round(v["expertise_score"], 2),
            })

        return {
            "decision_id": decision_id,
            "question": decision["question"],
            "status": decision["status"],
            "total_votes": len(votes),
            "perspectives_covered": list(perspectives_covered),
            "consensus": {
                "recommendation": winner,
                "support_pct": winner_pct,
                "strength": consensus_strength,
                "all_recommendations": normalized,
            },
            "votes": vote_details,
        }

    @mcp.tool()
    async def close_decision(decision_id: str, final_decision: str = "") -> dict:
        """Close a decision and record the final outcome.

        Locks the decision from further votes and records what was decided.

        Args:
            decision_id: The decision to close
            final_decision: The final decision taken (optional, uses consensus if empty)
        """
        conn = _get_db()

        decision = conn.execute(
            "SELECT * FROM decisions WHERE id = ?", (decision_id,)
        ).fetchone()
        if not decision:
            return {"error": f"Decision '{decision_id}' not found"}

        # Konsens berechnen für Confidence
        votes = conn.execute(
            "SELECT recommendation, confidence FROM votes WHERE decision_id = ?",
            (decision_id,)
        ).fetchall()

        if votes and not final_decision:
            # Automatisch den Konsens als Entscheidung nehmen
            rec_counts = {}
            for v in votes:
                rec = v["recommendation"].lower().strip()
                rec_counts[rec] = rec_counts.get(rec, 0) + v["confidence"]
            final_decision = max(rec_counts, key=rec_counts.get)

        avg_confidence = sum(v["confidence"] for v in votes) / len(votes) if votes else 0

        conn.execute("""
            UPDATE decisions SET
                status = 'closed',
                closed_at = ?,
                final_decision = ?,
                confidence = ?
            WHERE id = ?
        """, (datetime.utcnow().isoformat(), final_decision,
              round(avg_confidence, 2), decision_id))
        conn.commit()

        return {
            "status": "closed",
            "decision_id": decision_id,
            "final_decision": final_decision,
            "confidence": round(avg_confidence, 2),
            "total_votes": len(votes),
        }

    @mcp.tool()
    async def list_decisions(status: str = "all", limit: int = 20) -> dict:
        """List all decisions in the hive mind.

        Args:
            status: Filter by status ("open", "closed", "all")
            limit: Max results (default: 20)
        """
        conn = _get_db()

        if status == "all":
            rows = conn.execute(
                "SELECT * FROM decisions ORDER BY created_at DESC LIMIT ?", (limit,)
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM decisions WHERE status = ? ORDER BY created_at DESC LIMIT ?",
                (status, limit)
            ).fetchall()

        decisions = []
        for r in rows:
            vote_count = conn.execute(
                "SELECT COUNT(*) FROM votes WHERE decision_id = ?", (r["id"],)
            ).fetchone()[0]
            decisions.append({
                "id": r["id"],
                "question": r["question"],
                "status": r["status"],
                "votes": vote_count,
                "final_decision": r["final_decision"] or None,
                "confidence": r["confidence"],
                "created_at": r["created_at"],
            })

        return {"total": len(decisions), "filter": status, "decisions": decisions}

    @mcp.tool()
    async def get_agent_expertise(agent_id: str) -> dict:
        """Get an agent's expertise profile across all areas.

        Shows which areas an agent has voted on and their expertise scores.

        Args:
            agent_id: The agent to look up
        """
        conn = _get_db()
        rows = conn.execute("""
            SELECT area, score, total_votes, correct_votes
            FROM agent_expertise WHERE agent_id = ?
            ORDER BY score DESC
        """, (agent_id,)).fetchall()

        if not rows:
            return {"agent_id": agent_id, "message": "No expertise data yet."}

        areas = []
        for r in rows:
            areas.append({
                "area": r["area"],
                "expertise_score": round(r["score"], 2),
                "total_votes": r["total_votes"],
            })

        return {"agent_id": agent_id, "expertise_areas": areas}
