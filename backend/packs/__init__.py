"""Domain packs: the platform reads any document type via pluggable packs.

A pack is a mostly-declarative description of a document domain (its fields,
tables, arithmetic, identity, and optional similarity input). The generic engine
in base.py interprets that description — so adding a new domain is writing a
pack, not changing the engine.
"""

from .registry import all_domains, detect_domain, get_pack  # noqa: F401
