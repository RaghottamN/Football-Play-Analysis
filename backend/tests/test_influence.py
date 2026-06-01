"""
Unit Tests — Passing Network & Influence Scorer
"""
import sys
from pathlib import Path
import pandas as pd
import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))
from services.passing_network import (
    build_networkx_graph, compute_centrality_metrics, PassingNetworkService,
)
from services.influence_scorer import InfluenceScorer


class TestBuildNetworkxGraph:
    def test_empty_events(self):
        G = build_networkx_graph([], team='home')
        assert G.number_of_nodes() == 0

    def test_simple_pass(self):
        events = [{'from_player': '7', 'to_player': '9', 'team': 'home'}]
        G = build_networkx_graph(events, team='home')
        assert G.has_edge('7', '9')
        assert G['7']['9']['weight'] == 1

    def test_multiple_passes_same_pair(self):
        events = [
            {'from_player': '7', 'to_player': '9', 'team': 'home'},
            {'from_player': '7', 'to_player': '9', 'team': 'home'},
            {'from_player': '7', 'to_player': '9', 'team': 'home'},
        ]
        G = build_networkx_graph(events, team='home')
        assert G['7']['9']['weight'] == 3

    def test_team_filter(self):
        events = [
            {'from_player': '7', 'to_player': '9', 'team': 'home'},
            {'from_player': '4', 'to_player': '6', 'team': 'away'},
        ]
        G_home = build_networkx_graph(events, team='home')
        assert G_home.number_of_edges() == 1
        assert G_home.has_edge('7', '9')


class TestComputeCentralityMetrics:
    def setup_method(self):
        import networkx as nx
        self.G = nx.DiGraph()
        self.G.add_edge('7', '9', weight=5)
        self.G.add_edge('9', '11', weight=3)
        self.G.add_edge('7', '11', weight=2)
        self.G.add_edge('11', '7', weight=1)

    def test_all_metrics_present(self):
        metrics = compute_centrality_metrics(self.G)
        expected = ['degree_centrality', 'betweenness_centrality',
                    'closeness_centrality', 'eigenvector_centrality', 'pagerank']
        for key in expected:
            assert key in metrics, f"Missing metric: {key}"

    def test_pagerank_sums_to_one(self):
        metrics = compute_centrality_metrics(self.G)
        total = sum(metrics['pagerank'].values())
        assert abs(total - 1.0) < 0.01

    def test_all_nodes_have_scores(self):
        metrics = compute_centrality_metrics(self.G)
        for node in self.G.nodes():
            assert node in metrics['pagerank']

    def test_empty_graph_returns_empty_dicts(self):
        import networkx as nx
        metrics = compute_centrality_metrics(nx.DiGraph())
        assert metrics['pagerank'] == {}


class TestInfluenceScorer:
    def setup_method(self):
        self.scorer = InfluenceScorer(w_pagerank=0.4, w_betweenness=0.3, w_spatial=0.3)
        self.centrality = {
            'pagerank':               {'7': 0.4, '9': 0.35, '11': 0.25},
            'betweenness_centrality': {'7': 0.6, '9': 0.3,  '11': 0.1},
            'eigenvector_centrality': {'7': 0.5, '9': 0.3,  '11': 0.2},
        }
        self.spatial = {'7': 0.18, '9': 0.12, '11': 0.07}

    def test_weights_sum_to_one(self):
        assert abs(self.scorer.w_pr + self.scorer.w_bt + self.scorer.w_sp - 1.0) < 1e-6

    def test_compute_returns_sorted_list(self):
        records = self.scorer.compute(self.centrality, self.spatial)
        assert len(records) == 3
        pis_values = [r['pis'] for r in records]
        assert pis_values == sorted(pis_values, reverse=True)

    def test_all_records_have_rank(self):
        records = self.scorer.compute(self.centrality, self.spatial)
        for i, rec in enumerate(records, 1):
            assert rec['rank'] == i

    def test_pis_in_range(self):
        records = self.scorer.compute(self.centrality, self.spatial)
        for rec in records:
            assert 0.0 <= rec['pis'] <= 1.0

    def test_normalise_zero_range(self):
        values = {'a': 0.5, 'b': 0.5, 'c': 0.5}
        normed = InfluenceScorer._normalise(values)
        assert all(v == 0.5 for v in normed.values())

    def test_invalid_weights_raise(self):
        with pytest.raises(AssertionError):
            InfluenceScorer(w_pagerank=0.5, w_betweenness=0.5, w_spatial=0.5)

    def test_generate_insights_non_empty(self):
        records = self.scorer.compute(self.centrality, self.spatial)
        insights = self.scorer.generate_insights(records)
        assert len(insights) > 0
        assert 'Player' in insights[0]
