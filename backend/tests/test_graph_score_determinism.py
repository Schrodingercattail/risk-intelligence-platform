"""
Graph / cluster risk score determinism regression tests.

Root cause this guards against (observed as U00010 drifting 87.02 -> 86.14
across pipeline runs with an IDENTICAL feature vector):

    GraphAnalysisService._calculate_cluster_risk_score() ended with

        # Add some randomness for demo
        total_score += random.uniform(0, 20)

    Cluster risk feeds graph_score (cluster_risk*0.3 + min(size*5,30)),
    which feeds the final weighted risk_score (0.5/0.3/0.2). An unseeded
    random term there made EVERY pipeline run rescore every case
    differently: U00010's rule and ML components were bit-identical
    (85.00 / 99.41) while graph moved 59.08 -> 54.70 purely by chance.

A second, compounding bug: detect_all_clusters() INSERTed new clusters on
every run without clearing previous ones, so a user accumulated one extra
cluster membership per pipeline run. _calculate_graph_score SUMS over every
membership, so graph_score climbed toward its 100 cap with each rerun.

Invariants asserted here:
  1. cluster risk score is a pure function of the cluster's structure
  2. re-detection replaces (not appends to) previous detection results
  3. graph_score for the same membership set is stable across recomputation
"""
import asyncio
import sys
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import networkx as nx

from app.services.graph_service import GraphAnalysisService


def _svc():
    return GraphAnalysisService.__new__(GraphAnalysisService)


def _star_cluster(n_members: int, density: float = 1.0) -> nx.Graph:
    """A synthetic cluster graph with the requested size/density."""
    g = nx.Graph()
    nodes = [f"U{i:05d}" for i in range(n_members)]
    g.add_nodes_from(nodes)
    for i in range(n_members):
        for j in range(i + 1, n_members):
            g.add_edge(nodes[i], nodes[j], type="shared_device", weight=1)
    return g


class TestClusterRiskScoreDeterminism:
    def test_same_cluster_scores_identically_on_repeated_computation(self):
        """The primary regression: no random term in the score."""
        svc = _svc()
        g = _star_cluster(19)
        members = list(g.nodes())
        scores = [svc._calculate_cluster_risk_score(members, g) for _ in range(10)]
        assert len(set(scores)) == 1, \
            f"cluster risk score is nondeterministic: {scores}"

    def test_score_is_pure_function_of_structure(self):
        """Two structurally identical clusters score the same — the score
        must not depend on node identity or call order."""
        svc = _svc()
        g = _star_cluster(18)
        a = svc._calculate_cluster_risk_score(list(g.nodes()), g)
        # same structure, relabelled nodes
        h = nx.relabel_nodes(g, {n: f"X{n[1:]}" for n in g.nodes()})
        b = svc._calculate_cluster_risk_score(list(h.nodes()), h)
        assert a == b

    def test_no_unseeded_randomness_in_scoring_path(self):
        """The scorer source must not call the unseeded random module."""
        import ast
        import inspect
        import textwrap
        src = textwrap.dedent(inspect.getsource(
            GraphAnalysisService._calculate_cluster_risk_score))
        calls = {c.func.id for c in ast.walk(ast.parse(src))
                 if isinstance(c, ast.Call) and isinstance(c.func, ast.Name)}
        assert not any(n.startswith("random") for n in calls), \
            f"unseeded randomness reintroduced into cluster risk scoring: {calls}"

    def test_deterministic_formula(self):
        """size(min(n*10,50)) + density*30, capped at 100."""
        svc = _svc()
        # 19 members, density 1.0 -> 50 + 30 = 80
        assert svc._calculate_cluster_risk_score(list(_star_cluster(19).nodes()), _star_cluster(19)) == 80.0
        # 3 members, density 1.0 -> 30 + 30 = 60
        assert svc._calculate_cluster_risk_score(list(_star_cluster(3).nodes()), _star_cluster(3)) == 60.0
        # single member -> no connectivity term
        g = nx.Graph()
        g.add_node("U1")
        assert svc._calculate_cluster_risk_score(["U1"], g) == 10.0

    def test_larger_structure_scores_higher(self):
        """The score must still discriminate cluster sizes below saturation."""
        svc = _svc()
        s3 = svc._calculate_cluster_risk_score(list(_star_cluster(3).nodes()), _star_cluster(3))
        s10 = svc._calculate_cluster_risk_score(list(_star_cluster(10).nodes()), _star_cluster(10))
        assert s10 > s3, "cluster size must still contribute to the score"


class TestGraphScoreStability:
    def test_graph_score_stable_for_same_memberships(self):
        """_calculate_graph_score over an identical membership set is stable."""
        from app.services.risk_service import RiskScoringService

        class FixedResult:
            """A query result yielding the same membership rows every time."""
            def __init__(self, rows):
                self._rows = rows

            async def execute(self, *_a, **_k):
                return self._rows

            def __iter__(self):
                return iter(self._rows)

        rows = [(
            SimpleNamespace(role_in_cluster="spoke"),
            SimpleNamespace(risk_score=80.0, member_count=19),
        )]

        async def score_once():
            svc = RiskScoringService.__new__(RiskScoringService)
            svc.db = FixedResult(rows)
            return await svc._calculate_graph_score("U00010")

        vals = [asyncio.run(score_once()) for _ in range(5)]
        assert len(set(vals)) == 1, f"graph score unstable: {vals}"
        # 80.0*0.3 + min(19*5,30) = 24 + 30
        assert vals[0] == 54.0

    def test_graph_score_accumulating_memberships_sums(self):
        """Documents the accumulation hazard the re-detection fix prevents:
        two memberships for the same user SUM into a higher graph_score."""
        from app.services.risk_service import RiskScoringService

        class FixedResult:
            def __init__(self, rows):
                self._rows = rows

            async def execute(self, *_a, **_k):
                return self._rows

            def __iter__(self):
                return iter(self._rows)

        rows = [(
            SimpleNamespace(role_in_cluster="spoke"),
            SimpleNamespace(risk_score=80.0, member_count=19),
        )] * 2  # stale + fresh duplicate

        async def score():
            svc = RiskScoringService.__new__(RiskScoringService)
            svc.db = FixedResult(rows)
            return await svc._calculate_graph_score("U00010")

        assert asyncio.run(score()) == 100.0, \
            "duplicated memberships should sum to the cap — this is why " \
            "detect_all_clusters must clear previous results"

    def test_repeated_memberships_do_not_accumulate(self):
        """detect_all_clusters must REPLACE previous detections.

        Guards the compounding bug: users accumulated one extra cluster
        membership per pipeline run, summing graph_score toward the cap.
        """
        import inspect
        src = inspect.getsource(GraphAnalysisService.detect_all_clusters)
        assert "delete(ClusterMember)" in src, \
            "detect_all_clusters no longer clears previous detection results " \
            "(memberships accumulate and inflate graph_score on every rerun)"
        assert "delete(AccountCluster)" in src

