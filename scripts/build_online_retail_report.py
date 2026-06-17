from __future__ import annotations

import base64
from pathlib import Path
import re
from textwrap import dedent

import matplotlib.pyplot as plt
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
RAW_FILE = ROOT / "data" / "raw" / "Online Retail.xlsx"
PROCESSED_DIR = ROOT / "data" / "processed"
CHART_DIR = ROOT / "outputs" / "charts"
REPORT_FILE = ROOT / "outputs" / "online_retail_dashboard.html"


CATEGORY_PATTERNS = {
    "Home Decor": r"heart|holder|candle|lantern|frame|clock|mirror|sign|vase|decoration|decorative|light|wall",
    "Kitchen & Dining": r"cup|mug|plate|bowl|cake|tea|coffee|kitchen|cutlery|spoon|fork|glass|jar|bottle|napkin|doormat",
    "Gifts & Occasions": r"gift|birthday|party|wedding|set|wrap|ribbon|tag|card|present",
    "Holiday & Seasonal": r"christmas|xmas|easter|valentine|halloween|advent|snow|tree",
    "Storage & Bags": r"bag|box|basket|storage|tin|case|luggage|suitcase",
    "Apparel & Accessories": r"scarf|hat|glove|sock|jewellery|necklace|bracelet|ring|hair|purse",
    "Kids & Toys": r"toy|doll|game|child|children|baby|lunch box|school",
    "Bath & Beauty": r"bath|soap|towel|cosmetic|make up|perfume|toilet|wash",
    "Stationery": r"pen|pencil|notebook|paper|clip|sticker|memo|stationery",
}


REGIONS = {
    "United Kingdom": "United Kingdom",
    "EIRE": "Western Europe",
    "France": "Western Europe",
    "Germany": "Western Europe",
    "Netherlands": "Western Europe",
    "Belgium": "Western Europe",
    "Switzerland": "Western Europe",
    "Austria": "Western Europe",
    "Channel Islands": "Western Europe",
    "Spain": "Southern Europe",
    "Portugal": "Southern Europe",
    "Italy": "Southern Europe",
    "Greece": "Southern Europe",
    "Malta": "Southern Europe",
    "Cyprus": "Southern Europe",
    "Denmark": "Northern Europe",
    "Norway": "Northern Europe",
    "Sweden": "Northern Europe",
    "Finland": "Northern Europe",
    "Iceland": "Northern Europe",
    "Poland": "Central/Eastern Europe",
    "Czech Republic": "Central/Eastern Europe",
    "Lithuania": "Central/Eastern Europe",
    "Australia": "Oceania",
    "USA": "North America",
    "Canada": "North America",
    "Israel": "Middle East",
    "Bahrain": "Middle East",
    "United Arab Emirates": "Middle East",
    "Saudi Arabia": "Middle East",
    "Japan": "Asia",
    "Singapore": "Asia",
    "Hong Kong": "Asia",
    "RSA": "Africa",
    "Brazil": "South America",
    "European Community": "Western Europe",
    "Unspecified": "Unspecified",
}


def money(value: float) -> str:
    return f"£{value:,.0f}"


def pct(value: float) -> str:
    return f"{value:.1%}"


def classify_category(description: object) -> str:
    text = "" if pd.isna(description) else str(description).lower()
    for category, pattern in CATEGORY_PATTERNS.items():
        if re.search(pattern, text):
            return category
    return "Other / Mixed"


def is_merchandise(row: pd.Series) -> bool:
    stock_code = "" if pd.isna(row["StockCode"]) else str(row["StockCode"]).upper().strip()
    description = "" if pd.isna(row["Description"]) else str(row["Description"]).upper().strip()
    service_codes = {"POST", "DOT", "M", "BANK CHARGES", "AMAZONFEE", "S", "D", "CRUK", "C2"}
    service_terms = r"POSTAGE|DOTCOM POSTAGE|MANUAL|BANK CHARGES|AMAZON FEE|DISCOUNT|CRUK|CARRIAGE"
    return stock_code not in service_codes and re.search(service_terms, description) is None


def fig_to_base64(path: Path) -> str:
    return base64.b64encode(path.read_bytes()).decode("ascii")


def save_bar(
    df: pd.DataFrame,
    x: str,
    y: str,
    title: str,
    path: Path,
    color: str = "#2f6f73",
    xlabel: str = "Revenue (£)",
) -> None:
    plt.figure(figsize=(10, 5.8))
    plt.barh(df[x], df[y], color=color)
    plt.gca().invert_yaxis()
    plt.title(title, loc="left", fontsize=15, fontweight="bold")
    plt.xlabel(xlabel)
    plt.ylabel("")
    plt.grid(axis="x", alpha=0.22)
    plt.tight_layout()
    plt.savefig(path, dpi=180)
    plt.close()


def build_report() -> None:
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    CHART_DIR.mkdir(parents=True, exist_ok=True)

    raw = pd.read_excel(RAW_FILE)
    raw.columns = [c.strip() for c in raw.columns]
    raw_rows = len(raw)

    df = raw.copy()
    df["Description"] = df["Description"].astype("string").str.strip()
    df["Country"] = df["Country"].astype("string").str.strip()
    df["InvoiceNo"] = df["InvoiceNo"].astype("string").str.strip()
    df["StockCode"] = df["StockCode"].astype("string").str.strip()
    df["InvoiceDate"] = pd.to_datetime(df["InvoiceDate"], errors="coerce")

    df["IsCancellation"] = df["InvoiceNo"].str.startswith("C", na=False) | (df["Quantity"] < 0)
    cleaning_mask = (
        (~df["IsCancellation"])
        & df["InvoiceDate"].notna()
        & df["Description"].notna()
        & (df["Quantity"] > 0)
        & (df["UnitPrice"] > 0)
    )
    clean = df.loc[cleaning_mask].copy()
    clean["CustomerID"] = clean["CustomerID"].astype("Int64")
    clean["Revenue"] = clean["Quantity"] * clean["UnitPrice"]
    clean["Month"] = clean["InvoiceDate"].dt.to_period("M").dt.to_timestamp()
    clean["Date"] = clean["InvoiceDate"].dt.date
    clean["ProductCategory"] = clean["Description"].apply(classify_category)
    clean["Region"] = clean["Country"].map(REGIONS).fillna("Other International")
    clean["IsMerchandise"] = clean.apply(is_merchandise, axis=1)

    clean.to_csv(PROCESSED_DIR / "online_retail_cleaned.csv", index=False)
    merchandise = clean.loc[clean["IsMerchandise"]].copy()

    monthly = (
        clean.groupby("Month", as_index=False)
        .agg(Revenue=("Revenue", "sum"), Orders=("InvoiceNo", "nunique"), Units=("Quantity", "sum"))
        .sort_values("Month")
    )
    monthly["AverageOrderValue"] = monthly["Revenue"] / monthly["Orders"]
    monthly.to_csv(PROCESSED_DIR / "monthly_revenue.csv", index=False)

    products = (
        merchandise.groupby(["StockCode", "Description"], as_index=False)
        .agg(Revenue=("Revenue", "sum"), Units=("Quantity", "sum"), Orders=("InvoiceNo", "nunique"))
        .sort_values("Revenue", ascending=False)
    )
    products.to_csv(PROCESSED_DIR / "top_products.csv", index=False)

    products_by_units = products.sort_values("Units", ascending=False)
    products_by_units.to_csv(PROCESSED_DIR / "top_products_by_units.csv", index=False)

    regions = (
        clean.groupby("Region", as_index=False)
        .agg(Revenue=("Revenue", "sum"), Orders=("InvoiceNo", "nunique"), Customers=("CustomerID", "nunique"))
        .sort_values("Revenue", ascending=False)
    )
    regions.to_csv(PROCESSED_DIR / "region_revenue.csv", index=False)

    countries = (
        clean.groupby("Country", as_index=False)
        .agg(Revenue=("Revenue", "sum"), Orders=("InvoiceNo", "nunique"), Customers=("CustomerID", "nunique"))
        .sort_values("Revenue", ascending=False)
    )
    countries.to_csv(PROCESSED_DIR / "country_revenue.csv", index=False)

    categories = (
        merchandise.groupby("ProductCategory", as_index=False)
        .agg(Revenue=("Revenue", "sum"), Units=("Quantity", "sum"), Orders=("InvoiceNo", "nunique"))
        .sort_values("Revenue", ascending=False)
    )
    categories.to_csv(PROCESSED_DIR / "category_revenue.csv", index=False)

    customer_value = (
        clean.dropna(subset=["CustomerID"])
        .groupby("CustomerID", as_index=False)
        .agg(Revenue=("Revenue", "sum"), Orders=("InvoiceNo", "nunique"))
        .sort_values("Revenue", ascending=False)
    )
    customer_value.to_csv(PROCESSED_DIR / "customer_value.csv", index=False)

    monthly_plot = CHART_DIR / "monthly_revenue.png"
    plt.figure(figsize=(11, 5.8))
    plt.plot(monthly["Month"], monthly["Revenue"], color="#1f6f8b", linewidth=3, marker="o", markersize=4)
    plt.title("Monthly Revenue Trend", loc="left", fontsize=15, fontweight="bold")
    plt.ylabel("Revenue (£)")
    plt.xlabel("")
    plt.grid(axis="y", alpha=0.22)
    plt.tight_layout()
    plt.savefig(monthly_plot, dpi=180)
    plt.close()

    save_bar(
        products_by_units.head(10),
        "Description",
        "Units",
        "Top-Selling Products by Units",
        CHART_DIR / "top_products.png",
        xlabel="Units sold",
    )
    save_bar(categories.head(10), "ProductCategory", "Revenue", "Revenue by Product Category", CHART_DIR / "category_revenue.png", "#8a5a44")
    save_bar(regions.head(10), "Region", "Revenue", "Revenue by Region", CHART_DIR / "region_revenue.png", "#5f6f52")

    total_revenue = clean["Revenue"].sum()
    total_orders = clean["InvoiceNo"].nunique()
    total_units = clean["Quantity"].sum()
    total_customers = clean["CustomerID"].nunique()
    avg_order_value = total_revenue / total_orders
    removed_rows = raw_rows - len(clean)
    uk_share = countries.loc[countries["Country"] == "United Kingdom", "Revenue"].sum() / total_revenue
    top_product = products.iloc[0]
    top_selling_product = products_by_units.iloc[0]
    top_category = categories.iloc[0]
    top_region = regions.iloc[0]
    peak_month = monthly.loc[monthly["Revenue"].idxmax()]
    q4_revenue = monthly[monthly["Month"].dt.quarter == 4]["Revenue"].sum()
    q4_share = q4_revenue / total_revenue
    top_10_product_share = products.head(10)["Revenue"].sum() / merchandise["Revenue"].sum()
    top_10_customer_share = customer_value.head(10)["Revenue"].sum() / total_revenue

    def table_html(table: pd.DataFrame, money_cols: tuple[str, ...] = ("Revenue",)) -> str:
        display = table.copy()
        for col in money_cols:
            if col in display.columns:
                display[col] = display[col].map(money)
        for col in ("AverageOrderValue",):
            if col in display.columns:
                display[col] = display[col].map(money)
        if "Month" in display.columns:
            display["Month"] = pd.to_datetime(display["Month"]).dt.strftime("%b %Y")
        return display.to_html(index=False, classes="data-table", border=0, escape=False)

    cards = [
        ("Net Revenue", money(total_revenue), "After removing cancellations, returns, zero-price rows, and unusable product records."),
        ("Orders", f"{total_orders:,.0f}", f"Average order value: {money(avg_order_value)}."),
        ("Units Sold", f"{total_units:,.0f}", f"Across {total_customers:,.0f} identified customers."),
        ("Rows Cleaned Out", f"{removed_rows:,.0f}", f"{pct(removed_rows / raw_rows)} of raw rows excluded from sales analysis."),
    ]

    insight_items = [
        f"Revenue is highly seasonal: Q4 contributes {pct(q4_share)} of the cleaned revenue, with the peak month in {peak_month['Month']:%B %Y} at {money(peak_month['Revenue'])}.",
        f"The United Kingdom is the core market, generating {pct(uk_share)} of revenue. International growth should be treated as a targeted expansion play, not the current base business.",
        f"The top-selling merchandise product by units is {top_selling_product['Description']} with {top_selling_product['Units']:,.0f} units; the top merchandise product by revenue is {top_product['Description']} at {money(top_product['Revenue'])}.",
        f"The highest-value category is {top_category['ProductCategory']} at {money(top_category['Revenue'])}, while {top_region['Region']} is the highest-value region at {money(top_region['Revenue'])}.",
        f"The top 10 customers account for {pct(top_10_customer_share)} of revenue, making retention and account management material to protecting sales.",
    ]

    recommendations = [
        "Plan inventory and staffing around the Q4 surge, with replenishment triggers for high-volume gift, home, and dining items by late Q3.",
        "Protect the UK revenue base with loyalty offers, win-back campaigns, and post-purchase replenishment journeys before funding broad geographic expansion.",
        "Use category-level bundles: pair high-revenue home decor and kitchen items with seasonal gift packaging to increase average order value.",
        "Build a named-account retention workflow for the highest-value customers, including early access to seasonal ranges and volume incentives.",
        "Standardize product taxonomy at source. The current dataset requires keyword inference for categories, which is workable for analysis but too fragile for recurring management reporting.",
    ]

    html = f"""
    <!doctype html>
    <html lang="en">
    <head>
      <meta charset="utf-8">
      <meta name="viewport" content="width=device-width, initial-scale=1">
      <title>Online Retail Sales Analysis Dashboard</title>
      <style>
        :root {{
          --ink: #1e2528;
          --muted: #657174;
          --line: #d9e0df;
          --paper: #f7f8f5;
          --panel: #ffffff;
          --teal: #1f6f8b;
          --sage: #5f6f52;
          --clay: #8a5a44;
        }}
        * {{ box-sizing: border-box; }}
        body {{
          margin: 0;
          font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Arial, sans-serif;
          color: var(--ink);
          background: var(--paper);
          line-height: 1.45;
        }}
        header {{
          background: #243033;
          color: #fff;
          padding: 42px 6vw 34px;
        }}
        header p {{ max-width: 960px; color: #dbe4e3; margin: 10px 0 0; font-size: 17px; }}
        h1 {{ font-size: 38px; margin: 0; letter-spacing: 0; }}
        h2 {{ font-size: 22px; margin: 0 0 16px; }}
        h3 {{ font-size: 17px; margin: 0 0 8px; }}
        main {{ padding: 30px 6vw 50px; }}
        section {{ margin: 0 auto 30px; max-width: 1240px; }}
        .kpis {{
          display: grid;
          grid-template-columns: repeat(4, minmax(0, 1fr));
          gap: 14px;
        }}
        .card {{
          background: var(--panel);
          border: 1px solid var(--line);
          border-radius: 8px;
          padding: 18px;
        }}
        .metric {{ font-size: 28px; font-weight: 750; margin: 5px 0; color: var(--teal); }}
        .muted {{ color: var(--muted); font-size: 14px; }}
        .grid-2 {{
          display: grid;
          grid-template-columns: repeat(2, minmax(0, 1fr));
          gap: 18px;
        }}
        .chart {{
          width: 100%;
          display: block;
          border: 1px solid var(--line);
          border-radius: 8px;
          background: #fff;
        }}
        .insights {{
          display: grid;
          grid-template-columns: 1fr 1fr;
          gap: 18px;
        }}
        ul {{ margin: 0; padding-left: 20px; }}
        li {{ margin: 0 0 10px; }}
        .table-wrap {{ overflow-x: auto; background: #fff; border: 1px solid var(--line); border-radius: 8px; }}
        .data-table {{ width: 100%; border-collapse: collapse; font-size: 14px; }}
        .data-table th {{ text-align: left; background: #edf2f1; padding: 10px; }}
        .data-table td {{ border-top: 1px solid var(--line); padding: 10px; vertical-align: top; }}
        footer {{ max-width: 1240px; margin: 20px auto 0; color: var(--muted); font-size: 13px; }}
        @media (max-width: 900px) {{
          .kpis, .grid-2, .insights {{ grid-template-columns: 1fr; }}
          h1 {{ font-size: 30px; }}
          main, header {{ padding-left: 20px; padding-right: 20px; }}
        }}
      </style>
    </head>
    <body>
      <header>
        <h1>Online Retail Sales Analysis Dashboard</h1>
        <p>Client-ready sales analysis using the Online Retail transaction dataset referenced from Kaggle. The cleaned view focuses on valid sales transactions from {clean['InvoiceDate'].min():%d %b %Y} to {clean['InvoiceDate'].max():%d %b %Y}.</p>
      </header>
      <main>
        <section class="kpis">
          {''.join(f'<article class="card"><h3>{label}</h3><div class="metric">{value}</div><p class="muted">{note}</p></article>' for label, value, note in cards)}
        </section>

        <section class="grid-2">
          <article>
            <h2>Revenue Trends</h2>
            <img class="chart" src="data:image/png;base64,{fig_to_base64(monthly_plot)}" alt="Monthly revenue trend">
          </article>
          <article>
            <h2>Top-Selling Products</h2>
            <img class="chart" src="data:image/png;base64,{fig_to_base64(CHART_DIR / 'top_products.png')}" alt="Top-selling products by units">
          </article>
          <article>
            <h2>High-Value Categories</h2>
            <img class="chart" src="data:image/png;base64,{fig_to_base64(CHART_DIR / 'category_revenue.png')}" alt="Revenue by product category">
          </article>
          <article>
            <h2>High-Value Regions</h2>
            <img class="chart" src="data:image/png;base64,{fig_to_base64(CHART_DIR / 'region_revenue.png')}" alt="Revenue by region">
          </article>
        </section>

        <section class="insights">
          <article class="card">
            <h2>Business Insights</h2>
            <ul>{''.join(f'<li>{item}</li>' for item in insight_items)}</ul>
          </article>
          <article class="card">
            <h2>Recommendations</h2>
            <ul>{''.join(f'<li>{item}</li>' for item in recommendations)}</ul>
          </article>
        </section>

        <section>
          <h2>Top Products Table</h2>
          <div class="table-wrap">{table_html(products_by_units.head(12))}</div>
        </section>

        <section class="grid-2">
          <article>
            <h2>Category Detail</h2>
            <div class="table-wrap">{table_html(categories)}</div>
          </article>
          <article>
            <h2>Regional Detail</h2>
            <div class="table-wrap">{table_html(regions)}</div>
          </article>
        </section>

        <footer>
          Source: Kaggle dataset page provided by the user, with the public Online Retail workbook downloaded from the UCI Machine Learning Repository mirror because Kaggle requires authenticated file access. Cleaning excluded cancellations/returns, non-positive quantities, non-positive prices, missing invoice dates, and missing product descriptions. Product and category rankings exclude service/charge lines such as postage, manual adjustments, bank charges, and discounts. Product categories are keyword-derived from descriptions and should be replaced by a formal merchandising taxonomy for production reporting.
        </footer>
      </main>
    </body>
    </html>
    """

    REPORT_FILE.write_text(dedent(html).strip(), encoding="utf-8")

    summary = {
        "raw_rows": raw_rows,
        "clean_rows": len(clean),
        "total_revenue": total_revenue,
        "orders": total_orders,
        "units": int(total_units),
        "customers": int(total_customers),
        "date_start": str(clean["InvoiceDate"].min()),
        "date_end": str(clean["InvoiceDate"].max()),
        "top_product": str(top_product["Description"]),
        "top_product_revenue": float(top_product["Revenue"]),
        "top_selling_product": str(top_selling_product["Description"]),
        "top_selling_product_units": int(top_selling_product["Units"]),
        "top_category": str(top_category["ProductCategory"]),
        "top_region": str(top_region["Region"]),
    }
    pd.Series(summary).to_json(PROCESSED_DIR / "analysis_summary.json", indent=2)


if __name__ == "__main__":
    build_report()
