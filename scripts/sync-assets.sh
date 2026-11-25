#!/bin/bash
# Use the same mapping as the web build, including the root favicon and emblems.
exec node "$(dirname "$0")/../web/tools/sync-assets.mjs"
