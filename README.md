# Online Retail Sales Analysis

This folder contains a cleaned and organized sales analysis for the Online Retail dataset requested from Kaggle:

https://www.kaggle.com/datasets/ulrikthygepedersen/online-retail-dataset

Kaggle requires authenticated file access, so the workbook was downloaded from the public UCI Machine Learning Repository mirror of the same Online Retail transaction dataset.

## Dashboard

- View dashboard: https://htmlpreview.github.io/?https://github.com/DeepakPamisetty/FUTURE_DS_01/blob/main/outputs/online_retail_dashboard.html
- Dashboard file in repository: https://github.com/DeepakPamisetty/FUTURE_DS_01/blob/main/outputs/online_retail_dashboard.html
- GitHub Pages URL, after Pages is enabled: https://deepakpamisetty.github.io/FUTURE_DS_01/

The GitHub Pages URL returns 404 until Pages is enabled for this repository from **Settings > Pages**, using the `main` branch and `/root` folder.

## Outputs

- `outputs/online_retail_dashboard.html` - client-ready dashboard with KPI cards, charts, insights, and recommendations.
- `data/processed/online_retail_cleaned.csv` - cleaned transaction-level sales data.
- `data/processed/monthly_revenue.csv` - revenue, orders, units, and average order value by month.
- `data/processed/top_products_by_units.csv` - top-selling merchandise products by units sold.
- `data/processed/top_products.csv` - top merchandise products by revenue.
- `data/processed/category_revenue.csv` - keyword-derived category performance.
- `data/processed/region_revenue.csv` - region-level revenue performance.
- `data/processed/country_revenue.csv` - country-level revenue performance.
- `data/processed/customer_value.csv` - customer-level revenue and order counts.

## Cleaning Rules

Rows were excluded from sales analysis when they represented cancellations/returns, had missing invoice dates or product descriptions, non-positive quantities, or non-positive unit prices. Product and category rankings also exclude service or charge lines such as postage, manual adjustments, bank charges, carriage, and discounts.

The source data does not include a formal product category field. Categories in this analysis are inferred from product description keywords and should be replaced by a controlled merchandising taxonomy for recurring business reporting.

## Rebuild

```bash
MPLCONFIGDIR=/private/tmp python3 online_retail_analysis/scripts/build_online_retail_report.py
```
