#!/usr/bin/env python3
"""
Show recent agent responses from Redis STM, grouped by agent.

- Connects using Config.get_redis_connection_params()
- Scans stm:turn:{user_id}:* hashes
- Filters role == 'assistant'
- Groups by agent_name and prints the most recent N per agent

Usage examples:
  python scripts/show_agent_responses.py --user-id 12345 --per-agent 5
  python scripts/show_agent_responses.py --user-id 12345 --since-hours 24

Notes:
- Requires Redis running and your app writing turns to STM.
- Timestamps are expected in ISO format; older data is handled best-effort.
"""
import argparse
import sys
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List

# Ensure project root on import path (to import config)
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from config import Config  # type: ignore

try:
    import redis  # type: ignore
except ImportError as e:
    print("❌ redis Python package not installed. Install with: pip install redis")
    sys.exit(1)


def parse_args():
    p = argparse.ArgumentParser(description="Show recent agent responses from Redis STM (grouped by agent)")
    p.add_argument("--user-id", type=int, required=True, help="User ID whose session data to scan")
    p.add_argument("--per-agent", type=int, default=5, help="How many recent responses to show per agent")
    p.add_argument("--since-hours", type=int, default=72, help="Only include responses within the last N hours")
    p.add_argument("--max-keys", type=int, default=5000, help="Maximum number of turn keys to scan")
    return p.parse_args()


def iso_to_dt(value: str) -> datetime:
    try:
        return datetime.fromisoformat(value)
    except Exception:
        # Best-effort parse for variations
        try:
            return datetime.strptime(value, "%Y-%m-%d %H:%M:%S")
        except Exception:
            return datetime.min


def main():
    args = parse_args()

    # Connect to Redis using app config
    redis_params = Config.get_redis_connection_params()
    # Ensure decode_responses so we get strings
    redis_params["decode_responses"] = True

    try:
        r = redis.StrictRedis(**redis_params)
        r.ping()
    except Exception as e:
        print(f"❌ Failed to connect to Redis: {e}")
        print("Ensure Redis is running and REDIS_* settings are correct in your environment or .env file.")
        sys.exit(2)

    pattern = f"stm:turn:{args.user_id}:*"
    cutoff = datetime.now() - timedelta(hours=args.since_hours)

    # Collect assistant turns
    collected: List[Dict] = []
    scanned = 0
    try:
        for key in r.scan_iter(pattern, count=500):
            scanned += 1
            if scanned > args.max_keys:
                break
            data = r.hgetall(key) or {}
            if not data:
                continue
            if data.get("role") != "assistant":
                continue
            ts = iso_to_dt(data.get("ts", ""))
            if ts < cutoff:
                continue
            collected.append({
                "agent": data.get("agent_name", "Unknown"),
                "text": data.get("text", ""),
                "ts": ts,
                "key": key,
            })
    except Exception as e:
        print(f"❌ Error scanning Redis keys: {e}")
        sys.exit(3)

    if not collected:
        print(
            f"ℹ️ No assistant responses found for user {args.user_id} in the last {args.since_hours} hours.\n"
            "- Make sure the app has processed some queries for this user.\n"
            "- Or increase the --since-hours window."
        )
        return 0

    # Group by agent, sort by timestamp desc
    by_agent: Dict[str, List[Dict]] = {}
    for item in collected:
        by_agent.setdefault(item["agent"], []).append(item)
    for agent, items in by_agent.items():
        items.sort(key=lambda x: x["ts"], reverse=True)

    # Print
    print("\n🧾 Recent agent responses from STM (grouped by agent)")
    print("=" * 72)
    print(f"User ID: {args.user_id} | Window: last {args.since_hours}h | Max per agent: {args.per_agent}")
    print("=" * 72)

    total = 0
    for agent in sorted(by_agent.keys()):
        items = by_agent[agent][: args.per_agent]
        if not items:
            continue
        print(f"\n🤖 {agent} — {len(items)} shown")
        print("-" * 72)
        for i, it in enumerate(items, 1):
            ts_str = it["ts"].isoformat() if isinstance(it["ts"], datetime) else str(it["ts"])
            text = it["text"].strip().replace("\n", " ")
            if len(text) > 400:
                text = text[:397] + "..."
            print(f"[{ts_str}] #{i}: {text}")
            total += 1

    print("\n" + "=" * 72)
    print(f"Done. Printed {total} responses across {len(by_agent)} agents.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
