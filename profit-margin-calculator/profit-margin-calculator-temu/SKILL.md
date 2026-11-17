---
name: profit-margin-calculator-temu
description: "Temu cross-border profit margin calculator for sellers. Supports both Full-Managed (全托管供货模式) and Semi-Managed (半托管海外仓自履约模式). Calculate break-even supply price, domestic freight, quality inspection penalty reserves, return refund losses, and multi-currency exchange rates (RMB/USD)."
metadata: {"nexscope":{"emoji":"💰","category":"ecommerce"}}
---

# Profit Margin Calculator — Temu 💰

Calculate product profitability for cross-border sellers on Temu. Supports both **Full-Managed (全托管供货模式)** and **Semi-Managed (半托管海外仓模式)**.

## Installation

```bash
npx skills add nexscope-ai/eCommerce-Skills --skill profit-margin-calculator-temu -g
```

## Features

- **Full-Managed Mode (全托管)**: Input FOB cost, domestic shipping to Temu transit warehouse, packaging/labeling, and return/inspection fine reserve to calculate net supply profit (RMB) and break-even quote price.
- **Semi-Managed Mode (半托管)**: Model overseas warehouse fulfillment, local delivery, Temu commission, and "refund without return" (仅退款) risk reserves.
- **Currency Conversion**: Automatic dual-currency reporting (RMB & USD).
- **Pricing & Target Margin Recommendations**: Calculate target quoting prices for 15%, 20%, 25%, and 30% net margin.

## Usage

### Run Demo (Full-Managed Mode)

```bash
python3 profit-margin-calculator/profit-margin-calculator-temu/scripts/calculator.py --demo
```

### Run Demo in Chinese

```bash
python3 profit-margin-calculator/profit-margin-calculator-temu/scripts/calculator.py --demo --zh
```

### Semi-Managed Mode (半托管)

```bash
python3 profit-margin-calculator/profit-margin-calculator-temu/scripts/calculator.py '{"mode": "semi_managed", "selling_price_usd": 19.99, "product_cost_cny": 25.0, "overseas_shipping_usd": 4.50}'
```
