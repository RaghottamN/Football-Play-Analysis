"""
PDF Exporter Service
====================
NEW module — generates a formatted PDF report from analysis results.
Uses ReportLab for PDF generation.
"""

from pathlib import Path
from typing import Dict, Any
from loguru import logger

try:
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import cm
    from reportlab.lib import colors
    from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer,
                                     Table, TableStyle, HRFlowable, KeepTogether)
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False
    logger.warning("reportlab not installed — PDF export will be unavailable")


class PDFExporter:
    """
    NEW class — generates full analysis PDF reports.
    """

    PAGE_W, PAGE_H = A4 if REPORTLAB_AVAILABLE else (595, 842)

    def generate(self, result: Dict[str, Any], output_path: str) -> str:
        """Generate PDF report and save to output_path. Returns path."""
        if not REPORTLAB_AVAILABLE:
            logger.error("ReportLab not available — skipping PDF generation")
            return output_path

        doc    = SimpleDocTemplate(output_path, pagesize=A4,
                                   leftMargin=2*cm, rightMargin=2*cm,
                                   topMargin=2*cm, bottomMargin=2*cm)
        styles = getSampleStyleSheet()
        story  = []

        # ── Title ─────────────────────────────────────────────────────────────
        title_style = ParagraphStyle('Title', parent=styles['Title'],
                                     textColor=colors.HexColor('#1a1a2e'),
                                     fontSize=22, spaceAfter=8)
        story.append(Paragraph("⚽ Football Analytics Report", title_style))
        story.append(Paragraph(f"Job ID: {result.get('job_id', 'N/A')[:16]}...", styles['Normal']))
        story.append(Spacer(1, 0.4*cm))
        story.append(HRFlowable(width="100%", thickness=2, color=colors.HexColor('#e94560')))
        story.append(Spacer(1, 0.4*cm))

        # ── Video Metadata ────────────────────────────────────────────────────
        meta = result.get('video_metadata', {})
        story.append(Paragraph("Video Information", styles['Heading2']))
        meta_table = [
            ['Filename', meta.get('filename', '-')],
            ['Duration',  f"{meta.get('duration_sec', 0):.1f}s"],
            ['FPS',       f"{meta.get('fps', 0):.1f}"],
            ['Resolution', f"{meta.get('width', 0)}×{meta.get('height', 0)}"],
        ]
        story.append(self._make_table(meta_table))
        story.append(Spacer(1, 0.4*cm))

        # ── Possession ────────────────────────────────────────────────────────
        poss = result.get('possession_stats', {})
        story.append(Paragraph("Possession Statistics", styles['Heading2']))
        poss_table = [
            ['Team', 'Possession %'],
            ['Home', f"{poss.get('home_pct', 50):.1f}%"],
            ['Away', f"{poss.get('away_pct', 50):.1f}%"],
        ]
        story.append(self._make_table(poss_table, header=True))
        story.append(Spacer(1, 0.4*cm))

        # ── Territorial Dominance ─────────────────────────────────────────────
        pc = result.get('pitch_control', {}).get('summary', {})
        story.append(Paragraph("Territorial Dominance (Spearman 2018 Pitch Control)", styles['Heading2']))
        pc_table = [
            ['Metric', 'Home', 'Away'],
            ['Pitch Control %', f"{pc.get('home_dominance_pct', 50):.1f}%",
                                f"{pc.get('away_dominance_pct', 50):.1f}%"],
            ['Frames Analyzed', str(pc.get('frames_analyzed', 0)), '-'],
        ]
        story.append(self._make_table(pc_table, header=True))
        story.append(Spacer(1, 0.4*cm))

        # ── Passing Network ───────────────────────────────────────────────────
        net = result.get('passing_network', {}).get('summary', {})
        story.append(Paragraph("Passing Network Summary", styles['Heading2']))
        net_table = [
            ['Metric', 'Home', 'Away'],
            ['Total Passes',   str(net.get('home_total_passes', 0)), str(net.get('away_total_passes', 0))],
            ['Players Tracked', str(net.get('home_players', 0)),     str(net.get('away_players', 0))],
        ]
        story.append(self._make_table(net_table, header=True))
        story.append(Spacer(1, 0.4*cm))

        # ── Player Influence Rankings ─────────────────────────────────────────
        influence = result.get('influence_rankings', {})
        for team in ['home', 'away']:
            rankings = influence.get(team, [])[:5]
            if rankings:
                story.append(Paragraph(f"Player Influence Rankings — {team.title()}", styles['Heading2']))
                table_data = [['Rank', 'Player', 'PIS', 'PageRank', 'Betweenness', 'Spatial']]
                for rec in rankings:
                    table_data.append([
                        str(rec.get('rank', '-')),
                        f"Player {rec.get('player_id', '-')}",
                        f"{rec.get('pis', 0):.3f}",
                        f"{rec.get('pagerank', 0):.3f}",
                        f"{rec.get('betweenness', 0):.3f}",
                        f"{rec.get('spatial_dominance', 0)*100:.1f}%",
                    ])
                story.append(self._make_table(table_data, header=True))
                story.append(Spacer(1, 0.3*cm))

        # ── AI Insights ───────────────────────────────────────────────────────
        ai = result.get('ai_insights', {})
        story.append(Paragraph("AI-Generated Insights", styles['Heading2']))
        for insight in ai.get('key_insights', []):
            story.append(Paragraph(f"• {insight}", styles['Normal']))
        story.append(Spacer(1, 0.3*cm))
        narrative = ai.get('match_narrative', '')
        if narrative:
            story.append(Paragraph("Match Narrative", styles['Heading3']))
            story.append(Paragraph(narrative, styles['Normal']))

        # ── Tactical Patterns ─────────────────────────────────────────────────
        tactics = result.get('tactical_insights', {})
        story.append(Spacer(1, 0.4*cm))
        story.append(Paragraph("Tactical Pattern Analysis", styles['Heading2']))
        ft = tactics.get('field_tilt', {})
        wing = tactics.get('wing_attacks', {})
        tact_table = [
            ['Pattern', 'Home', 'Away'],
            ['Field Tilt %', f"{ft.get('home', 50):.1f}%", f"{ft.get('away', 50):.1f}%"],
            ['Left Flank Attacks', f"{wing.get('left_flank_pct', 33):.1f}%", '-'],
            ['Center Attacks',     f"{wing.get('center_pct', 33):.1f}%", '-'],
            ['Right Flank Attacks', f"{wing.get('right_flank_pct', 33):.1f}%", '-'],
        ]
        story.append(self._make_table(tact_table, header=True))

        # ── Footer ────────────────────────────────────────────────────────────
        story.append(Spacer(1, 0.8*cm))
        story.append(HRFlowable(width="100%", thickness=1, color=colors.grey))
        footer_style = ParagraphStyle('Footer', parent=styles['Normal'],
                                      fontSize=8, textColor=colors.grey)
        story.append(Paragraph(
            "Pitch Control: Spearman (2018) Beyond Expected Goals · "
            "Network: Friends-of-Tracking-Data-FoTD · "
            "Tactical Metrics: football-match-intelligence (MIT)",
            footer_style
        ))

        doc.build(story)
        logger.info(f"PDF report generated: {output_path}")
        return output_path

    @staticmethod
    def _make_table(data, header=False):
        """Create a styled ReportLab Table."""
        col_width = (A4[0] - 4*cm) / max(len(data[0]), 1) if REPORTLAB_AVAILABLE else 100
        t = Table(data, colWidths=[col_width] * len(data[0]))
        style = [
            ('GRID',       (0, 0), (-1, -1), 0.5, colors.lightgrey),
            ('FONTNAME',   (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE',   (0, 0), (-1, -1), 9),
            ('PADDING',    (0, 0), (-1, -1), 4),
            ('ROWBACKGROUNDS', (0, 0), (-1, -1), [colors.white, colors.HexColor('#f8f9fa')]),
        ]
        if header:
            style += [
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1a1a2e')),
                ('TEXTCOLOR',  (0, 0), (-1, 0), colors.white),
                ('FONTNAME',   (0, 0), (-1, 0), 'Helvetica-Bold'),
            ]
        t.setStyle(TableStyle(style))
        return t
