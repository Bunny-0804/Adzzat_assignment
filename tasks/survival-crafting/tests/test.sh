#!/bin/bash
set -u
set -o pipefail

mkdir -p /logs/verifier
cd /app

# Force clean rebuild so copybook (.cpy) edits always recompile dependent .o objects
find /app -name "*.o" -delete && make > /logs/verifier/build.log 2>&1
if [ $? -ne 0 ]; then
  echo 0 > /logs/verifier/reward.txt
  exit 0
fi

pytest -v /tests/test_outputs.py 2>&1 | tee /logs/verifier/pytest.log
if [ ${PIPESTATUS[0]} -eq 0 ]; then
  echo 1 > /logs/verifier/reward.txt
else
  echo 0 > /logs/verifier/reward.txt
fi
