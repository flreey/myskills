#!/usr/bin/env bash
set -euo pipefail

PROBLEM="${*:-}"

if [ -z "$PROBLEM" ]; then
  echo "Usage: ./bin/system-skill.sh \"Your problem here\""
  exit 1
fi

cat <<PROMPT
Use the System Evolution Analyst Skill to analyze the following problem.

Problem:
$PROBLEM

Please output these sections:
1. Problem Restatement
2. Problem Type
3. System Boundary
4. Information Layer
5. Energy / Resource Layer
6. Feedback Layer
7. Failure Diagnosis
8. Smallest Useful Experiment
9. Evolution Roadmap
10. Practical Next Step

Be direct, critical, and practical. Separate facts, assumptions, hypotheses, and advice.
PROMPT
