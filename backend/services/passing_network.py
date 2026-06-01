"""
Passing Network Service
=======================
ADAPTED from:
  Friends-of-Tracking-Data-FoTD/passing-networks-in-python (MIT)
  Authors: Sergio Llana (@SergioMinuto90), Laurie Shaw (@EightyFivePoint)

Adaptations:
  1. PassingNetworkBuilder ABC preserved — adapted for our tracking dict format
  2. Possession phase detection logic from MetricaTrackingPassingNetwork._context_frames()
     adapted to work with our event timeline (not Metrica CSV format)
  3. draw_pass_map() logic preserved but output converted to Plotly JSON (not matplotlib)
  4. EXTENDED with NetworkX centrality metrics (NEW):
     - degree_centrality, betweenness_centrality, closeness_centrality,
       eigenvector_centrality, pagerank

NEW additions:
  - PassingNetworkService: main API-facing service
  - build_networkx_graph(): creates DiGraph from pass events
  - compute_centrality_metrics(): all 5 metrics + PageRank
  - to_plotly_json(): convert network to React-renderable format
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Tuple, Any
import numpy as np
import pandas as pd
import networkx as nx
from loguru import logger


# ─────────────────────────────────────────────────────────────────────────────
# ADAPTED from passing-networks-in-python/processing/ (MIT)
# Original: Sergio Llana (@SergioMinuto90), Laurie Shaw (@EightyFivePoint)
# ─────────────────────────────────────────────────────────────────────────────

class PassingNetworkBuilder(ABC):
    """
    Abstract base class for building passing networks.
    ADAPTED from passing-networks-in-python/processing/__init__.py (MIT).
    Interface preserved; data format adapted for our pipeline.
    """
    @abstractmethod
    def prepare_data(self): pass

    @abstractmethod
    def compute_metrics(self): pass


def _context_frames_from_events(
    events_df: pd.DataFrame,
    team_name: str,
) -> Tuple[set, set]:
    """
    Detect possession frames from our event timeline.

    ADAPTED from passing-networks-in-python/processing/tracking.py
    MetricaTrackingPassingNetwork._context_frames() (MIT).
    Original logic preserved; adapted for our event schema.

    Returns:
        on_ball_frames: set of frame indices when team_name has possession
        off_ball_frames: set of frame indices when team_name is defending
    """
    if events_df.empty or 'event_type' not in events_df.columns:
        return set(), set()

    possession_start_events  = ['pass', 'recovery', 'set_piece', 'shot']
    possession_change_events = ['ball_lost', 'ball_out', 'possession_change']

    on_ball_frames  = set()
    off_ball_frames = set()

    current_start = 0
    for _, row in events_df.iterrows():
        event_type = row.get('event_type', '')
        if event_type in possession_change_events:
            end_frame = int(row.get('frame_idx', 0))
            if row.get('team', '') == team_name:
                on_ball_frames.update(range(current_start, end_frame))
            else:
                off_ball_frames.update(range(current_start, end_frame))
            current_start = end_frame

    return on_ball_frames, off_ball_frames


# ─────────────────────────────────────────────────────────────────────────────
# NEW: NetworkX graph construction and centrality computation
# ─────────────────────────────────────────────────────────────────────────────

def build_networkx_graph(
    pass_events: List[Dict],
    team: str = 'home',
) -> nx.DiGraph:
    """
    Build a directed weighted NetworkX graph from pass events.
    NEW function — not in any source repository.

    Args:
        pass_events: list of {'from_player': str, 'to_player': str, 'team': str, ...}
        team: which team's passes to include

    Returns:
        DiGraph where edge weight = pass count
    """
    G = nx.DiGraph()
    for evt in pass_events:
        if evt.get('team', team) != team:
            continue
        src = str(evt.get('from_player', '?'))
        dst = str(evt.get('to_player',   '?'))
        if src == '?' or dst == '?':
            continue
        if G.has_edge(src, dst):
            G[src][dst]['weight'] += 1
        else:
            G.add_edge(src, dst, weight=1)
    return G


def compute_centrality_metrics(G: nx.DiGraph) -> Dict[str, Dict[str, float]]:
    """
    Compute all 5 centrality metrics + PageRank on a passing network graph.
    NEW function — not in any source repository.

    Returns:
        {
          'degree_centrality':      {player_id: float, ...},
          'betweenness_centrality': {player_id: float, ...},
          'closeness_centrality':   {player_id: float, ...},
          'eigenvector_centrality': {player_id: float, ...},
          'pagerank':               {player_id: float, ...},
        }
    """
    if G.number_of_nodes() == 0:
        return {k: {} for k in [
            'degree_centrality', 'betweenness_centrality',
            'closeness_centrality', 'eigenvector_centrality', 'pagerank'
        ]}

    metrics: Dict[str, Dict] = {}

    # Degree centrality (in + out combined)
    in_deg  = nx.in_degree_centrality(G)
    out_deg = nx.out_degree_centrality(G)
    metrics['degree_centrality'] = {
        n: round((in_deg.get(n, 0) + out_deg.get(n, 0)) / 2, 4)
        for n in G.nodes()
    }

    # Betweenness centrality (weighted)
    metrics['betweenness_centrality'] = {
        n: round(v, 4)
        for n, v in nx.betweenness_centrality(G, weight='weight', normalized=True).items()
    }

    # Closeness centrality
    metrics['closeness_centrality'] = {
        n: round(v, 4)
        for n, v in nx.closeness_centrality(G, distance='weight').items()
    }

    # Eigenvector centrality (with fallback for non-convergence)
    try:
        eig = nx.eigenvector_centrality(G, weight='weight', max_iter=1000)
    except (nx.PowerIterationFailedConvergence, nx.NetworkXError):
        logger.warning("Eigenvector centrality did not converge — using degree proxy")
        eig = metrics['degree_centrality']
    metrics['eigenvector_centrality'] = {n: round(v, 4) for n, v in eig.items()}

    # PageRank
    metrics['pagerank'] = {
        n: round(v, 4)
        for n, v in nx.pagerank(G, weight='weight', alpha=0.85).items()
    }

    return metrics


# ─────────────────────────────────────────────────────────────────────────────
# NEW: PassingNetworkService — full API-facing service
# ─────────────────────────────────────────────────────────────────────────────

class PassingNetworkService(PassingNetworkBuilder):
    """
    Full passing network service.
    Extends PassingNetworkBuilder ABC (adapted from passing-networks-in-python).
    Adds NetworkX centrality, Plotly JSON export, and structured API output.

    NEW class — not in any source repository.
    """

    def __init__(self):
        self.events_df:          Optional[pd.DataFrame] = None
        self.tracking_frames:    Optional[List[Dict]]   = None

        self.player_positions:   Optional[pd.DataFrame] = None
        self.player_pass_count:  Optional[pd.DataFrame] = None
        self.pair_pass_count:    Optional[pd.DataFrame] = None
        self.graph_home:         Optional[nx.DiGraph]   = None
        self.graph_away:         Optional[nx.DiGraph]   = None
        self.centrality_home:    Optional[Dict]         = None
        self.centrality_away:    Optional[Dict]         = None

    def load(self, events_df: pd.DataFrame, tracking_frames: List[Dict]) -> 'PassingNetworkService':
        self.events_df       = events_df
        self.tracking_frames = tracking_frames
        return self

    def prepare_data(self):
        """
        Prepare DataFrames for network visualization.
        Logic inspired by MetricaBasicPassingNetwork.prepare_data() (MIT).
        Adapted for our event schema.
        """
        if self.events_df is None or self.events_df.empty:
            logger.warning("No events — using empty passing network")
            self._init_empty()
            if self.tracking_frames:
                self.player_positions = self._positions_from_tracking()
            return

        passes = self.events_df[self.events_df['event_type'] == 'pass'].copy() \
            if 'event_type' in self.events_df.columns else pd.DataFrame()

        if passes.empty:
            self._init_empty()
            if self.tracking_frames:
                self.player_positions = self._positions_from_tracking()
            return

        # Player pass counts
        if 'from_player' in passes.columns:
            self.player_pass_count = passes.groupby('from_player').size().to_frame('num_passes')
        else:
            self._init_empty()
            return

        # Pair pass counts
        passes['pair_key'] = passes.apply(
            lambda r: '_'.join(sorted([str(r.get('from_player', '')), str(r.get('to_player', ''))])),
            axis=1
        )
        self.pair_pass_count = passes.groupby('pair_key').size().to_frame('num_passes')

        # Player positions (median location of pass origin)
        if 'start_x' in passes.columns and 'start_y' in passes.columns:
            self.player_positions = passes.groupby('from_player').agg(
                origin_pos_x=('start_x', 'median'),
                origin_pos_y=('start_y', 'median'),
            )
        elif self.tracking_frames:
            self.player_positions = self._positions_from_tracking()

    def compute_metrics(self):
        """Build NetworkX graphs and compute all centrality metrics."""
        if self.events_df is None:
            return
        pass_events = self.events_df[self.events_df['event_type'] == 'pass'].to_dict('records') \
            if 'event_type' in self.events_df.columns else []

        self.graph_home = build_networkx_graph(pass_events, team='home')
        self.graph_away = build_networkx_graph(pass_events, team='away')

        self.centrality_home = compute_centrality_metrics(self.graph_home)
        self.centrality_away = compute_centrality_metrics(self.graph_away)

    def to_api_response(self) -> Dict[str, Any]:
        """
        Return full network data as JSON-serializable dict for FastAPI.
        Visualization logic adapted from passing-networks-in-python/visualization/ (MIT).
        Output format changed from matplotlib to Plotly JSON for React frontend.
        """
        self.prepare_data()
        self.compute_metrics()

        return {
            'home': self._team_network_json('home', self.graph_home, self.centrality_home),
            'away': self._team_network_json('away', self.graph_away, self.centrality_away),
            'summary': self._summary(),
        }

    def _team_network_json(
        self,
        team: str,
        graph: Optional[nx.DiGraph],
        centrality: Optional[Dict],
    ) -> Dict:
        """Format one team's network as Plotly-compatible JSON."""
        if graph is None or graph.number_of_nodes() == 0:
            return {'nodes': [], 'edges': [], 'centrality': {}}

        nodes = []
        for node in graph.nodes():
            pos_x, pos_y = 0.0, 0.0
            if self.player_positions is not None and node in self.player_positions.index:
                pos_x = float(self.player_positions.loc[node, 'origin_pos_x'])
                pos_y = float(self.player_positions.loc[node, 'origin_pos_y'])

            nodes.append({
                'id':    node,
                'label': f"P{node}",
                'x':     pos_x,
                'y':     pos_y,
                'passes': int(graph.out_degree(node, weight='weight')),
                'pagerank':    round(centrality['pagerank'].get(node, 0), 4) if centrality else 0,
                'betweenness': round(centrality['betweenness_centrality'].get(node, 0), 4) if centrality else 0,
                'degree':      round(centrality['degree_centrality'].get(node, 0), 4) if centrality else 0,
            })

        edges = []
        for src, dst, data in graph.edges(data=True):
            edges.append({
                'source': src,
                'target': dst,
                'weight': data.get('weight', 1),
            })

        return {
            'nodes':      nodes,
            'edges':      edges,
            'centrality': centrality or {},
        }

    def _summary(self) -> Dict:
        g_home = self.graph_home
        g_away = self.graph_away
        pos = self.player_positions
        n_home = g_home.number_of_nodes() if g_home else 0
        n_away = g_away.number_of_nodes() if g_away else 0
        # Fall back to counted tracked players when network is empty
        if n_home == 0 and n_away == 0 and pos is not None and not pos.empty:
            n_total = len(pos)
            n_home  = n_total // 2
            n_away  = n_total - n_home
        return {
            'home_total_passes': int(sum(d['weight'] for _, _, d in g_home.edges(data=True))) if g_home else 0,
            'away_total_passes': int(sum(d['weight'] for _, _, d in g_away.edges(data=True))) if g_away else 0,
            'home_players':      n_home,
            'away_players':      n_away,
        }

    def _positions_from_tracking(self) -> pd.DataFrame:
        """Compute average player positions from tracking frames."""
        pos: Dict[str, List] = {}
        for frame in self.tracking_frames or []:
            for p in frame.get('home_players', []) + frame.get('away_players', []):
                pid = str(p.get('player_id', p.get('track_id', '')))
                if pid not in pos:
                    pos[pid] = []
                pos[pid].append((p.get('x', 0.0), p.get('y', 0.0)))
        records = [
            {'player_id': pid,
             'origin_pos_x': np.median([p[0] for p in coords]),
             'origin_pos_y': np.median([p[1] for p in coords])}
            for pid, coords in pos.items()
        ]
        df = pd.DataFrame(records).set_index('player_id') if records else pd.DataFrame(
            columns=['origin_pos_x', 'origin_pos_y'])
        return df

    def _init_empty(self):
        self.player_pass_count = pd.DataFrame(columns=['num_passes'])
        self.pair_pass_count   = pd.DataFrame(columns=['num_passes'])
        self.player_positions  = pd.DataFrame(columns=['origin_pos_x', 'origin_pos_y'])
