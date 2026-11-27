"""Language packs — per-language search implementations behind the /es routes.

Each pack owns: its Qdrant collection, its query exact-match arms, and the
result shaping its dictionary needs. The Japanese pipeline still lives in
app.retrieval (the JMdict-era code paths); new packs start small here and
migrate shared machinery (RRF fusion, embedder, telemetry) rather than
duplicating it.
"""
