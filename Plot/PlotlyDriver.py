from html import escape
from pathlib import Path
from typing import Iterable, Optional

from Chan import CChan
from Common.CEnum import KL_TYPE

from .PlotMeta import CChanPlotMeta


LEVEL_LABELS = {
    KL_TYPE.K_DAY: "日线",
    KL_TYPE.K_30M: "30分钟线",
    KL_TYPE.K_5M: "5分钟线",
}


def _level_label(level: KL_TYPE) -> str:
    return LEVEL_LABELS.get(level, level.name.replace("K_", ""))


def _date_at(meta: CChanPlotMeta, x: int):
    if not meta.datetick:
        return x
    idx = min(max(int(x), 0), len(meta.datetick) - 1)
    return meta.datetick[idx]


class CPlotlyDriver:
    def __init__(self, chan: CChan, level: KL_TYPE):
        self.code = chan.code
        self.level = level
        self.meta = CChanPlotMeta(chan[level])
        self.figure = self._build_figure()

    def _build_figure(self):
        go = _load_graph_objects()
        fig = go.Figure()
        self._draw_kline(fig, go)
        self._draw_lines(fig, go, self.meta.bi_list, "笔", "#111111", 2)
        self._draw_lines(fig, go, self.meta.seg_list, "线段", "#238b45", 4)
        self._draw_zs(fig, go)
        self._draw_bs_point(fig, go)
        fig.update_layout(
            title=f"{self.code} / {_level_label(self.level)}",
            xaxis_title="时间",
            yaxis_title="价格",
            hovermode="x",
            dragmode="zoom",
            showlegend=True,
            margin={"l": 48, "r": 24, "t": 56, "b": 40},
            xaxis={
                "rangeslider": {"visible": False},
                "tickmode": "auto",
                "nticks": 8,
                "tickangle": -20,
                "automargin": True,
            },
            template="plotly_white",
        )
        return fig

    def _draw_kline(self, fig, go):
        klu_list = list(self.meta.klu_iter())
        fig.add_trace(go.Candlestick(
            x=[klu.time.to_str() for klu in klu_list],
            open=[klu.open for klu in klu_list],
            high=[klu.high for klu in klu_list],
            low=[klu.low for klu in klu_list],
            close=[klu.close for klu in klu_list],
            name="K线",
        ))

    def _draw_lines(self, fig, go, items, name: str, color: str, width: int):
        for idx, item in enumerate(items):
            fig.add_trace(go.Scatter(
                x=[_date_at(self.meta, item.begin_x), _date_at(self.meta, item.end_x)],
                y=[item.begin_y, item.end_y],
                mode="lines",
                line={"color": color, "width": width, "dash": "solid" if item.is_sure else "dash"},
                name=name,
                legendgroup=name,
                showlegend=idx == 0,
            ))

    def _draw_zs(self, fig, go):
        for idx, zs in enumerate(self.meta.zs_lst):
            self._draw_one_zs(fig, go, zs, idx == 0)

    def _draw_one_zs(self, fig, go, zs, showlegend: bool):
        x0 = _date_at(self.meta, zs.begin)
        x1 = _date_at(self.meta, zs.end)
        fig.add_trace(go.Scatter(
            x=[x0, x1, x1, x0, x0],
            y=[zs.low, zs.low, zs.high, zs.high, zs.low],
            mode="lines",
            fill="toself",
            fillcolor="rgba(255, 165, 0, 0.12)",
            line={"color": "#f59f00", "width": 2, "dash": "solid" if zs.is_sure else "dash"},
            name="中枢",
            legendgroup="中枢",
            showlegend=showlegend,
        ))
        for sub_zs in zs.sub_zs_lst:
            self._draw_one_zs(fig, go, sub_zs, False)

    def _draw_bs_point(self, fig, go):
        if not self.meta.bs_point_lst:
            return
        fig.add_trace(go.Scatter(
            x=[_date_at(self.meta, bsp.x) for bsp in self.meta.bs_point_lst],
            y=[bsp.y for bsp in self.meta.bs_point_lst],
            mode="markers+text",
            marker={
                "size": 10,
                "symbol": ["triangle-up" if bsp.is_buy else "triangle-down" for bsp in self.meta.bs_point_lst],
                "color": ["#d62728" if bsp.is_buy else "#2ca02c" for bsp in self.meta.bs_point_lst],
            },
            text=[bsp.desc() for bsp in self.meta.bs_point_lst],
            textposition=["bottom center" if bsp.is_buy else "top center" for bsp in self.meta.bs_point_lst],
            name="买卖点",
        ))

    def save2html(self, path, drivers: Optional[Iterable["CPlotlyDriver"]] = None, code: Optional[str] = None):
        driver_list = list(drivers) if drivers is not None else [self]
        self.save_multi_level_html(driver_list, path, code or self.code)

    @staticmethod
    def save_multi_level_html(drivers: Iterable["CPlotlyDriver"], path, code: str):
        driver_list = list(drivers)
        html_parts = []
        for idx, driver in enumerate(driver_list):
            include_plotlyjs = "cdn" if idx == 0 else False
            fig_html = driver.figure.to_html(
                full_html=False,
                include_plotlyjs=include_plotlyjs,
                config={"responsive": True},
            )
            html_parts.append(
                f'<section class="chart-section"><h2>{escape(_level_label(driver.level))}</h2>{fig_html}</section>'
            )

        output = Path(path)
        output.write_text(_render_html(code, html_parts), encoding="utf-8")


def _load_graph_objects():
    try:
        import plotly.graph_objects as go
    except ImportError as exc:
        raise RuntimeError("生成 HTML 图表需要安装 plotly，请先安装项目依赖。") from exc
    return go


def _render_html(code: str, chart_sections: list[str]) -> str:
    body = "\n".join(chart_sections)
    title = f"{code} 缠论分析"
    return f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{escape(title)}</title>
  <style>
    body {{
      margin: 0;
      background: #f6f7f9;
      color: #1f2933;
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    }}
    header {{
      padding: 20px 28px 8px;
    }}
    h1 {{
      margin: 0;
      font-size: 24px;
      font-weight: 700;
    }}
    .chart-section {{
      margin: 16px 20px 24px;
      padding: 16px 16px 8px;
      background: #ffffff;
      border: 1px solid #d8dee6;
      border-radius: 6px;
    }}
    h2 {{
      margin: 0 0 8px;
      font-size: 18px;
      font-weight: 650;
    }}
  </style>
</head>
<body>
  <header><h1>{escape(title)}</h1></header>
  <main>
{body}
  </main>
</body>
</html>
"""
