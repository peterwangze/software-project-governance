"""Check-domain modules extracted from verify_workflow.py.

Established in 0.59.0 (DEC-083 Phase 1) to start the incremental
per-domain split of the verify_workflow.py God Module. Each module owns
one check domain and is imported back into verify_workflow.py, which
degrades into a thin dispatch entry point over the 0.59.0~0.64.0
roadmap. The manifest domain is the first extracted scope.
"""
