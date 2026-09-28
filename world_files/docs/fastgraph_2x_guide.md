# fastgraph 2.x User Guide

Last updated for fastgraph 2.4 (March 2026).

## Installing

    pip install fastgraph==2.4

Supports Python 3.9 and newer.

## Creating a graph

    from fastgraph import Graph

    g = Graph()                      # uses the in-memory backend by default
    g.add_node("a")
    g.add_node("b")
    g.add_edge("a", "b", 2.5)        # third argument is the edge weight

## Algorithms

    from fastgraph.algorithms import shortest_path

    path = shortest_path(g, "a", "b")

## Saving

    g.save("graph.fg")
    g2 = Graph.load("graph.fg")

## Roadmap

fastgraph 3.0 is planned for later this year. Expect some breaking changes.
Details will be published in the 3.0 release notes.
