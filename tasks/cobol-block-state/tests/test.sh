#!/bin/bash
set -u

mkdir -p /logs/verifier
cd /app

make
if [ $? -ne 0 ]; then
  echo 0 > /logs/verifier/reward.txt
  exit 0
fi

pytest -v /tests/test_outputs.py
if [ $? -eq 0 ]; then
  echo 1 > /logs/verifier/reward.txt
else
  echo 0 > /logs/verifier/reward.txt
fi
