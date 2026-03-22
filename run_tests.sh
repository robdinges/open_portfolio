#!/bin/bash
# Run tests with correct PYTHONPATH for OpenPortfolio

export PYTHONPATH=src
.venv/bin/python -m pytest "$@"
