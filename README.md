# GST Invoice Matcher

Interactive web app for matching company invoices with portal data using Streamlit.

## Quick Start

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Features

- **Drag & Drop Interface** - Upload Excel files easily
- **Real-time Matching** - Instant results with progress tracking  
- **Visual Analytics** - Charts and metrics for match results
- **Buffer Matching** - Fuzzy matching with amount tolerance
- **Export Results** - Download matched/unmatched data as Excel

## File Format

**Company Data:** GSTIN of supplier, Party Name, Accounting Document No, Invoice No, Invoice Date, CGST Amount, SGST Amount, IGST Amount

**Portal Data:** GSTIN of supplier, Invoice number, Invoice Date, Central Tax(₹), State/UT Tax(₹), Integrated Tax(₹)

## Configuration

Edit `config.json` to customize column mappings and date formats.

## CLI Version

```bash
python main.py
```

Original command-line version still available.
