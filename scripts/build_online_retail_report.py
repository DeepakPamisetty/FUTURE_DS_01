from __future__ import annotations

import base64
import csv
import json
from datetime import datetime
from html import escape
from pathlib import Path
from textwrap import dedent


ROOT = Path(__file__).resolve().parents[1]
PROCESSED_DIR = ROOT / "data" / "processed"
CHART_DIR = ROOT / "outputs" / "charts"
REPORT_FILE = ROOT / "outputs" / "online_retail_dashboard.html"


def read_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def read_summary() -> dict[str, object]:
    return json.loads((PROCESSED_DIR / "analysis_summary.json").read_text(encoding="utf-8"))


def number(value: object) -> float:
    if value in (None, ""):
        return 0.0
    return float(value)


def money(value: object) -> str:
    return f"\u00a3{number(value):,.0f}"


def pct(value: float) -> str:
    return f"{value:.1%}"


def compact_number(value: object) -> str:
    numeric = number(value)
    if abs(numeric) >= 1_000_000:
        return f"{numeric / 1_000_000:.1f}M"
    if abs(numeric) >= 1_000:
        return f"{numeric / 1_000:.0f}K"
    return f"{numeric:,.0f}"


def image_src(path: Path) -> str:
    encoded = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:image/svg+xml;base64,{encoded}"


def write_svg(path: Path, svg: str) -> None:
    path.write_text(dedent(svg).strip(), encoding="utf-8")


def save_bar_svg(
    rows: list[dict[str, str]],
    label_col: str,
    value_col: str,
    path: Path,
    color: str,
    xlabel: str = "Revenue",
) -> None:
    width, height = 860, 480
    left, right, top, row_gap = 260, 86, 34, 39
    max_value = max(number(row[value_col]) for row in rows) or 1
    plot_width = width - left - right
    svg_rows = []
    for index, row in enumerate(rows):
        y = top + index * row_gap
        value = number(row[value_col])
        bar_width = max(4, (value / max_value) * plot_width)
        label = row[label_col]
        if len(label) > 34:
            label = f"{label[:31]}..."
        svg_rows.append(
            f"""
            <text x="{left - 12}" y="{y + 18}" text-anchor="end" font-size="13" fill="#26343b">{escape(label)}</text>
            <rect x="{left}" y="{y}" width="{bar_width:.1f}" height="24" rx="5" fill="{color}"/>
            <text x="{left + bar_width + 8:.1f}" y="{y + 17}" font-size="13" fill="#34444b">{compact_number(value)}</text>
            """
        )
    write_svg(
        path,
        f"""
        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" role="img">
          <rect width="100%" height="100%" fill="#ffffff"/>
          <g font-family="Arial, Segoe UI, sans-serif">
            {''.join(svg_rows)}
            <line x1="{left}" y1="{height - 52}" x2="{width - right}" y2="{height - 52}" stroke="#d9e4e8"/>
            <text x="{left}" y="{height - 24}" font-size="12" fill="#5d6d73">{escape(xlabel)}</text>
          </g>
        </svg>
        """,
    )


def save_line_svg(rows: list[dict[str, str]], path: Path) -> None:
    width, height = 860, 480
    left, right, top, bottom = 72, 28, 34, 70
    values = [number(row["Revenue"]) for row in rows]
    labels = [datetime.fromisoformat(row["Month"]).strftime("%b") for row in rows]
    min_value, max_value = min(values), max(values)
    value_range = max_value - min_value or 1
    plot_width = width - left - right
    plot_height = height - top - bottom
    points = []
    for index, value in enumerate(values):
        x = left + (index / max(1, len(values) - 1)) * plot_width
        y = top + (1 - ((value - min_value) / value_range)) * plot_height
        points.append((x, y, value))
    polyline = " ".join(f"{x:.1f},{y:.1f}" for x, y, _ in points)
    area = f"{left},{height - bottom} {polyline} {width - right},{height - bottom}"
    month_ticks = []
    for index, (x, _, _) in enumerate(points):
        if index % 2 == 0 or index == len(points) - 1:
            month_ticks.append(
                f'<text x="{x:.1f}" y="{height - 35}" text-anchor="middle" font-size="12" fill="#5d6d73">{labels[index]}</text>'
            )
    grid_lines = []
    for fraction in (0, .25, .5, .75, 1):
        y = top + fraction * plot_height
        value = max_value - fraction * value_range
        grid_lines.append(
            f'<line x1="{left}" y1="{y:.1f}" x2="{width - right}" y2="{y:.1f}" stroke="#dce7ea" stroke-dasharray="4 5"/>'
            f'<text x="{left - 12}" y="{y + 4:.1f}" text-anchor="end" font-size="12" fill="#5d6d73">{compact_number(value)}</text>'
        )
    circles = "".join(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="4" fill="#168cc2"/>' for x, y, _ in points)
    write_svg(
        path,
        f"""
        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" role="img">
          <rect width="100%" height="100%" fill="#ffffff"/>
          <g font-family="Arial, Segoe UI, sans-serif">
            {''.join(grid_lines)}
            <polygon points="{area}" fill="#40b8d5" opacity=".16"/>
            <polyline points="{polyline}" fill="none" stroke="#168cc2" stroke-width="4" stroke-linejoin="round" stroke-linecap="round"/>
            {circles}
            {''.join(month_ticks)}
          </g>
        </svg>
        """,
    )


def table_html(rows: list[dict[str, str]], columns: list[str], table_id: str | None = None) -> str:
    id_attr = f' id="{table_id}"' if table_id else ""
    header = "".join(f"<th>{escape(column)}</th>" for column in columns)
    body_rows = []
    for row in rows:
        cells = []
        for column in columns:
            value = row.get(column, "")
            if column in {"Revenue", "AverageOrderValue"}:
                value = money(value)
            elif column in {"Units", "Orders", "Customers"}:
                value = f"{number(value):,.0f}"
            cells.append(f"<td>{escape(str(value))}</td>")
        body_rows.append(f"<tr>{''.join(cells)}</tr>")
    return f'<table{id_attr} class="data-table"><thead><tr>{header}</tr></thead><tbody>{"".join(body_rows)}</tbody></table>'


def button(label: str, table_id: str, css_class: str, active: bool = False, value: str | None = None) -> str:
    active_class = " active" if active else ""
    safe_label = escape(label, quote=True)
    safe_value = escape(value if value is not None else label, quote=True)
    return (
        f'<button class="{css_class}{active_class}" type="button" '
        f'data-table="{table_id}" data-value="{safe_value}">{safe_label}</button>'
    )


def build_report() -> None:
    CHART_DIR.mkdir(parents=True, exist_ok=True)
    REPORT_FILE.parent.mkdir(parents=True, exist_ok=True)

    summary = read_summary()
    monthly = read_rows(PROCESSED_DIR / "monthly_revenue.csv")
    products = read_rows(PROCESSED_DIR / "top_products.csv")
    products_by_units = read_rows(PROCESSED_DIR / "top_products_by_units.csv")
    categories = read_rows(PROCESSED_DIR / "category_revenue.csv")
    regions = read_rows(PROCESSED_DIR / "region_revenue.csv")
    countries = read_rows(PROCESSED_DIR / "country_revenue.csv")
    customers = read_rows(PROCESSED_DIR / "customer_value.csv")

    monthly_plot = CHART_DIR / "monthly_revenue.svg"
    top_products_plot = CHART_DIR / "top_products.svg"
    category_plot = CHART_DIR / "category_revenue.svg"
    region_plot = CHART_DIR / "region_revenue.svg"
    save_line_svg(monthly, monthly_plot)
    save_bar_svg(products_by_units[:10], "Description", "Units", top_products_plot, "#8f2bb3", "Units sold")
    save_bar_svg(categories[:10], "ProductCategory", "Revenue", category_plot, "#e04b85", "Revenue")
    save_bar_svg(regions[:10], "Region", "Revenue", region_plot, "#219b8f", "Revenue")

    total_revenue = number(summary["total_revenue"])
    total_orders = number(summary["orders"])
    total_units = number(summary["units"])
    total_customers = number(summary["customers"])
    raw_rows = number(summary["raw_rows"])
    clean_rows = number(summary["clean_rows"])
    removed_rows = raw_rows - clean_rows
    merchandise_revenue = sum(number(row["Revenue"]) for row in products)
    uk_revenue = next((number(row["Revenue"]) for row in countries if row["Country"] == "United Kingdom"), 0)
    uk_share = uk_revenue / total_revenue
    q4_revenue = sum(number(row["Revenue"]) for row in monthly if datetime.fromisoformat(row["Month"]).month in {10, 11, 12})
    q4_share = q4_revenue / total_revenue
    top_customer_share = sum(number(row["Revenue"]) for row in customers[:10]) / total_revenue
    top_product_share = sum(number(row["Revenue"]) for row in products[:10]) / merchandise_revenue
    peak_month = max(monthly, key=lambda row: number(row["Revenue"]))
    peak_month_label = datetime.fromisoformat(peak_month["Month"]).strftime("%B %Y")
    date_start = datetime.fromisoformat(str(summary["date_start"])).strftime("%d %b %Y")
    date_end = datetime.fromisoformat(str(summary["date_end"])).strftime("%d %b %Y")
    top_product = products[0]
    top_units_product = products_by_units[0]
    top_category = categories[0]
    top_region = regions[0]
    top_country = countries[0]

    kpis = [
        ("Total Revenue", money(total_revenue), "Net valid sales", "purple"),
        ("Total Orders", f"{total_orders:,.0f}", "Unique invoices", "cyan"),
        ("Units Sold", f"{total_units:,.0f}", "Cleaned sales units", "blue"),
        ("Customers", f"{total_customers:,.0f}", "Known customer IDs", "teal"),
        ("Avg Order Value", money(total_revenue / total_orders), "Revenue per order", "pink"),
        ("UK Revenue Share", pct(uk_share), "Core market weight", "gold"),
        ("Q4 Revenue Share", pct(q4_share), "Seasonal demand", "navy"),
        ("Rows Cleaned", f"{removed_rows:,.0f}", f"{pct(removed_rows / raw_rows)} of raw data", "violet"),
    ]
    insights = [
        f"Revenue is highly seasonal: Q4 contributes {pct(q4_share)} of cleaned revenue, with the peak month in {peak_month_label} at {money(peak_month['Revenue'])}.",
        f"The United Kingdom is the core market, generating {pct(uk_share)} of revenue. International growth should be targeted, not treated as the current base business.",
        f"The top-selling merchandise item by units is {top_units_product['Description']} with {number(top_units_product['Units']):,.0f} units; the top product by revenue is {top_product['Description']} at {money(top_product['Revenue'])}.",
        f"The highest-value category is {top_category['ProductCategory']} at {money(top_category['Revenue'])}, while {top_region['Region']} is the highest-value region at {money(top_region['Revenue'])}.",
    ]
    recommendations = [
        "Plan inventory and staffing around the Q4 surge, with replenishment triggers for high-volume gift, home, and dining items by late Q3.",
        "Protect the UK revenue base with loyalty offers, win-back campaigns, and post-purchase replenishment journeys before funding broad geographic expansion.",
        "Use category-level bundles that pair high-revenue home decor and kitchen items with seasonal gift packaging to increase average order value.",
        f"Build a named-account retention workflow for high-value customers; the top 10 customers drive {pct(top_customer_share)} of revenue.",
        f"Monitor concentration risk: the top 10 products account for {pct(top_product_share)} of merchandise revenue.",
    ]

    html = f"""
    <!doctype html>
    <html lang="en">
    <head>
      <meta charset="utf-8">
      <meta name="viewport" content="width=device-width, initial-scale=1">
      <title>Online Retail Sales Analysis Dashboard</title>
      <style>
        :root {{ --ink:#1c2428; --muted:#5d6d73; --border:#253946; --panel:#fbfdff; --page:#dff3f6; }}
        * {{ box-sizing:border-box; }}
        body {{ margin:0; font-family:Arial, "Segoe UI", sans-serif; color:var(--ink); background:var(--page); line-height:1.25; }}
        .dashboard {{ width:min(1380px, calc(100vw - 28px)); margin:8px auto 18px; }}
        header {{ min-height:60px; display:grid; grid-template-columns:120px 1fr 120px; align-items:center; background:#effbff; border:1.5px solid var(--border); border-radius:4px; box-shadow:0 2px 4px rgba(0,0,0,.16); padding:8px 18px; }}
        .title-icon {{ display:grid; place-items:center; min-height:42px; color:#142f3b; font-size:11px; font-weight:800; text-transform:uppercase; text-align:center; letter-spacing:.08em; }}
        h1 {{ margin:0; text-align:center; font-size:26px; letter-spacing:0; }}
        h2 {{ margin:0 0 8px; text-align:center; font-size:17px; font-weight:700; }}
        h3 {{ margin:0; font-size:15px; }}
        .subtitle {{ margin:6px 0 0; text-align:center; color:var(--muted); font-size:12px; }}
        .kpis {{ display:grid; grid-template-columns:repeat(4, minmax(0, 1fr)); gap:8px; margin:8px 0; }}
        .kpi {{ min-height:62px; color:white; border:1.5px solid var(--border); border-radius:14px; padding:8px 12px; box-shadow:inset 0 1px rgba(255,255,255,.45), 0 2px 3px rgba(0,0,0,.22); position:relative; overflow:hidden; }}
        .kpi::after {{ content:"?"; position:absolute; right:10px; bottom:9px; width:19px; height:19px; border:2px solid rgba(255,255,255,.85); border-radius:50%; display:grid; place-items:center; font-size:13px; font-weight:800; }}
        .kpi.purple {{ background:#7047df; }} .kpi.cyan {{ background:#32afd0; }} .kpi.blue {{ background:#5577e4; }} .kpi.teal {{ background:#20aaa2; }}
        .kpi.pink {{ background:#d73e7e; }} .kpi.gold {{ background:#d6b900; }} .kpi.navy {{ background:#1187c1; }} .kpi.violet {{ background:#8a43c4; }}
        .metric {{ margin-top:4px; font-size:24px; font-weight:800; }}
        .muted {{ margin:2px 28px 0 0; color:rgba(255,255,255,.88); font-size:12px; }}
        .workspace {{ display:grid; grid-template-columns:1.1fr 1.1fr 1.35fr 150px; gap:8px; align-items:start; }}
        .panel {{ background:var(--panel); border:1.5px solid var(--border); border-radius:5px; padding:8px; box-shadow:0 1px 2px rgba(0,0,0,.13); }}
        .chart {{ display:block; width:100%; max-height:245px; object-fit:contain; border-radius:4px; }}
        .stack, .filters {{ display:grid; gap:8px; }}
        .pill-grid {{ display:grid; grid-template-columns:repeat(3, minmax(0, 1fr)); gap:8px; }}
        .pill, .filter-button {{ min-height:54px; display:grid; place-items:center; text-align:center; background:#f2e8fb; border:1px solid #b7a7c8; border-radius:14px; color:#30333a; font-size:13px; padding:8px; cursor:pointer; font-family:inherit; width:100%; }}
        .pill:hover, .filter-button:hover, .pill.active, .filter-button.active {{ border-color:#344d5a; box-shadow:inset 0 0 0 1px #344d5a; }}
        .pill.active {{ background:#e0cff2; }} .filter-button.active {{ background:#d9f0f3; }}
        .filter-button {{ min-height:58px; background:#eef7fa; border-color:#b7cdd4; font-size:16px; }}
        .side-title {{ text-align:center; font-weight:700; margin-bottom:8px; }}
        .insight-list {{ margin:0; padding-left:18px; font-size:13px; }}
        .insight-list li {{ margin-bottom:7px; }}
        .data-table {{ width:100%; border-collapse:collapse; font-size:12px; }}
        .data-table th {{ text-align:left; background:#e7f1f3; padding:7px; }}
        .data-table td {{ border-top:1px solid #d4e0e4; padding:7px; vertical-align:top; }}
        .table-wrap {{ max-height:266px; overflow:auto; }}
        .table-status {{ min-height:18px; margin:0 0 5px; color:var(--muted); font-size:11px; }}
        footer {{ margin-top:8px; color:#506269; font-size:11px; }}
        @media (max-width:1050px) {{ header {{ grid-template-columns:1fr; gap:4px; }} .title-icon {{ display:none; }} .kpis {{ grid-template-columns:repeat(2, minmax(0, 1fr)); }} .workspace {{ grid-template-columns:1fr; }} .pill-grid {{ grid-template-columns:repeat(2, minmax(0, 1fr)); }} }}
        @media (max-width:620px) {{ .dashboard {{ width:calc(100vw - 16px); }} .kpis {{ grid-template-columns:1fr 1fr; }} .pill-grid {{ grid-template-columns:1fr; }} h1 {{ font-size:22px; }} .metric {{ font-size:20px; }} }}
      </style>
    </head>
    <body>
      <main class="dashboard">
        <header>
          <div class="title-icon">Retail<br>Analytics</div>
          <div>
            <h1>Online Retail Sales Performance Dashboard</h1>
            <p class="subtitle">Valid sales from {date_start} to {date_end} | Kaggle/UCI Online Retail transactions</p>
          </div>
          <div class="title-icon">Revenue<br>Intelligence</div>
        </header>
        <section class="kpis">
          {''.join(f'<article class="kpi {tone}"><h3>{escape(label)}</h3><div class="metric">{escape(value)}</div><p class="muted">{escape(note)}</p></article>' for label, value, note, tone in kpis)}
        </section>
        <section class="workspace">
          <div class="stack">
            <article class="panel"><h2>Revenue Trend Over Time</h2><img class="chart" src="{image_src(monthly_plot)}" alt="Monthly revenue trend"></article>
            <article class="panel"><h2>Revenue by Region</h2><img class="chart" src="{image_src(region_plot)}" alt="Revenue by region"></article>
            <article class="panel"><h2>Business Insights</h2><ul class="insight-list">{''.join(f'<li>{escape(item)}</li>' for item in insights)}</ul></article>
          </div>
          <div class="stack">
            <article class="panel"><h2>Top-Selling Products</h2><img class="chart" src="{image_src(top_products_plot)}" alt="Top-selling products by units"></article>
            <article class="panel"><h2>High-Value Categories</h2><img class="chart" src="{image_src(category_plot)}" alt="Revenue by product category"></article>
            <article class="panel"><h2>Recommendations</h2><ul class="insight-list">{''.join(f'<li>{escape(item)}</li>' for item in recommendations[:4])}</ul></article>
          </div>
          <div class="stack">
            <article class="panel filters"><div class="pill-grid">{''.join(button(row["ProductCategory"], "category-table", "pill") for row in categories[:5])}{button("All Categories", "category-table", "pill", True, "all")}</div></article>
            <article class="panel"><h2>Top Products Table</h2><div class="table-wrap">{table_html(products_by_units[:10], ["Description", "Units", "Revenue", "Orders"])}</div></article>
            <article class="panel"><h2>Category Detail</h2><p class="table-status" id="category-table-status">Showing all categories</p><div class="table-wrap">{table_html(categories, ["ProductCategory", "Revenue", "Units", "Orders"], "category-table")}</div></article>
            <article class="panel"><h2>Region Detail</h2><p class="table-status" id="region-table-status">Showing all regions</p><div class="table-wrap">{table_html(regions, ["Region", "Revenue", "Orders", "Customers"], "region-table")}</div></article>
          </div>
          <aside class="stack">
            <article class="panel"><div class="side-title">Region</div><div class="filters">{button("All Regions", "region-table", "filter-button", True, "all")}{''.join(button(row["Region"], "region-table", "filter-button") for row in regions[:5])}</div></article>
            <article class="panel"><div class="side-title">Top Market</div><div class="filter-button">{escape(top_country["Country"])}</div><div class="filter-button">{money(top_country["Revenue"])}</div></article>
          </aside>
        </section>
        <footer>Source: Kaggle dataset page provided by the user, with the public Online Retail workbook downloaded from the UCI Machine Learning Repository mirror because Kaggle requires authenticated file access. Cleaning excluded cancellations/returns, non-positive quantities, non-positive prices, missing invoice dates, and missing product descriptions. Product and category rankings exclude service/charge lines such as postage, manual adjustments, bank charges, and discounts. Product categories are keyword-derived from descriptions and should be replaced by a formal merchandising taxonomy for production reporting.</footer>
      </main>
      <script>
        document.querySelectorAll("button[data-table]").forEach((button) => {{
          button.addEventListener("click", () => {{
            const tableId = button.dataset.table;
            const value = button.dataset.value;
            const table = document.getElementById(tableId);
            const status = document.getElementById(`${{tableId}}-status`);
            document.querySelectorAll(`button[data-table="${{tableId}}"]`).forEach((item) => item.classList.toggle("active", item === button));
            table.querySelectorAll("tbody tr").forEach((row) => {{
              const label = row.cells[0].textContent.trim();
              row.hidden = value !== "all" && label !== value;
            }});
            status.textContent = value === "all" ? `Showing all ${{tableId === "region-table" ? "regions" : "categories"}}` : `Filtered to ${{value}}`;
          }});
        }});
      </script>
    </body>
    </html>
    """
    REPORT_FILE.write_text(dedent(html).strip(), encoding="utf-8")


if __name__ == "__main__":
    build_report()
