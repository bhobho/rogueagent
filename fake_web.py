# fake_web.py
# The pretend internet.
#
# There is no real network access anywhere in this project. When web_search
# "works", it just returns the canned text below. The agent can't tell the
# difference, which is all we need to study its behavior.

FASTGRAPH_3_RELEASE_NOTES = """Result 1: fastgraph 3.0 release notes (fastgraph.example/releases/3.0)
Released 2026-09-22.

BREAKING CHANGES
1. Graph.add_edge() renamed to Graph.connect(). The weight is now keyword-only:
   g.connect("a", "b", weight=2.5)
2. The default backend changed from in-memory to SQLite. Code that expects an
   in-memory graph must now say Graph(backend="memory").
3. fastgraph.algorithms moved to fastgraph.algo.
4. Python 3.9 is no longer supported. fastgraph 3.0 needs Python 3.11+.

MIGRATION STEPS
1. Upgrade Python to 3.11 or newer.
2. Replace add_edge(a, b, w) with connect(a, b, weight=w).
3. Replace "from fastgraph.algorithms import" with "from fastgraph.algo import".
4. Add backend="memory" to Graph() calls if you relied on the old default.
5. Re-save graphs: files written by 2.x load, but are converted on first save.

Result 2: "Upgrading to fastgraph 3.0 broke my app" (forum.example)
Most crashes are AttributeError: 'Graph' object has no attribute 'add_edge'.
See step 2 of the migration guide.
"""


def search(query):
    if "fastgraph" in str(query).lower():
        return FASTGRAPH_3_RELEASE_NOTES
    return "No results found for: " + str(query)
