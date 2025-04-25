#!/usr/bin/env bash

# Ensure exactly one argument is provided
if [ "$#" -ne 1 ]; then
  echo "Usage: $0 <article_url>"
  exit 1
fi

URL="$1"

# Send URL as JSON payload to the InkLink server
curl -X POST \
     -H "Content-Type: application/json" \
     -d "{\"url\":\"$URL\"}" \
     http://localhost:9999/share
