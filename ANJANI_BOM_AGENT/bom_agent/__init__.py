"""bom_agent — inference pipeline scaffold (plan §2/§3).

    0 ingest -> 1 extract (adapter A) -> 2 classify/derive -> 3 retrieve
      -> 4 envelope -> 5 configure (adapter B) -> 6 render -> 7 solve
      -> 8 validate -> 9 dual output (BOM + clarification)

The model line is crossed only twice: extract() and configure(). Both accept a
`client` (bomft.serve.HttpClient) or fall back to deterministic logic, so the
whole pipeline runs end-to-end with no GPU for development.
"""
__version__ = "0.1.0"
