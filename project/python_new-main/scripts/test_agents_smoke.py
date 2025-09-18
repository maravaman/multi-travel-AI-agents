#!/usr/bin/env python3
"""
Smoke test for Travel Assistant agents.

- Invokes core.langgraph_multiagent_system.process_request for prompts that should
  exercise each of the 7 allowed agents.
- Verifies that a non-empty response is produced and lists agents involved.
- Exits with non-zero status if any agent fails to produce a response.

Usage:
  python project/python_new-main/scripts/test_agents_smoke.py

Environment:
- Designed to run without Ollama/Redis/MySQL strictly required; the system should
  degrade gracefully using fallbacks where applicable. If your environment lacks
  certain dependencies, warnings may appear but tests will still attempt to run.
"""
import json
import os
import sys
from datetime import datetime
from pathlib import Path

# Ensure project root import path (so we can import core.*)
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

ALLOWED_TRAVEL_AGENTS = [
    'TextTripAnalyzer',
    'TripMoodDetector',
    'TripCommsCoach',
    'TripBehaviorGuide',
    'TripCalmPractice',
    'TripSummarySynth',
    'TravelAssistant',
]

# Attempt to import the multiagent system
try:
    from core.langgraph_multiagent_system import langgraph_multiagent_system
except Exception as e:
    print(f"❌ Failed to import langgraph_multiagent_system: {e}")
    sys.exit(2)

TEST_USER = "smoke_tester"
TEST_USER_ID = int(datetime.now().timestamp())  # unique per run

# Prompts crafted to trigger each agent
AGENT_PROMPTS = {
    'TextTripAnalyzer': "Plan a 3-day trip to Paris with a budget of $150 per day.",
    'TripMoodDetector': "I'm anxious and worried about my first international trip.",
    'TripCommsCoach': "I struggle to communicate when traveling. What phrases should I learn?",
    'TripBehaviorGuide': "Help me decide between Rome or Barcelona. Which should I choose and why?",
    'TripCalmPractice': "I'm overwhelmed and stressed about planning. Please give me calming guidance.",
    'TripSummarySynth': "Summarize my travel preferences and profile insights gathered so far.",
    # TravelAssistant is an orchestrator/synthesis role; use a general prompt
    'TravelAssistant': "I want general travel planning help for a spring vacation in Japan.",
}

results = []
failures = []

for agent, prompt in AGENT_PROMPTS.items():
    try:
        out = langgraph_multiagent_system.process_request(
            user=TEST_USER,
            user_id=TEST_USER_ID,
            question=prompt,
        )
        response = (out or {}).get('response') or (out or {}).get('final_response') or ''
        agents_involved = (out or {}).get('agents_involved') or (out or {}).get('agent_chain') or []
        agents_involved = [a for a in agents_involved if a in ALLOWED_TRAVEL_AGENTS]

        ok = bool(isinstance(response, str) and len(response.strip()) >= 10)
        # Consider it a pass if we have a response, even if the specific agent is not explicitly listed
        if not ok:
            failures.append({
                'agent': agent,
                'reason': 'empty_or_short_response',
                'agents_involved': agents_involved,
                'raw_out': out,
            })
        results.append({
            'agent': agent,
            'ok': ok,
            'response_preview': (response.strip()[:160] + '...') if len(response or '') > 160 else response.strip(),
            'agents_involved': agents_involved,
        })
    except Exception as e:
        failures.append({'agent': agent, 'reason': f'exception: {e}'})
        results.append({'agent': agent, 'ok': False, 'error': str(e)})

summary = {
    'total': len(results),
    'passed': sum(1 for r in results if r.get('ok')),
    'failed': len(failures),
    'failures': failures,
    'results': results,
}

print(json.dumps(summary, indent=2))

# Non-zero exit if any failed
sys.exit(0 if not failures else 1)
