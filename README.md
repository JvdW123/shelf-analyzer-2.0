# Shelf Analyzer 2.0

Upload supermarket shelf photos, get structured Excel reports with SKU-level data.

**Live app:** https://shelf-analyzer-20.streamlit.app/

---

## How to Use

1. **Upload photos + metadata** — Enter store details (country, city, retailer, store format, shelf location, currency), upload shelf photos, tag each as Overview or Close-up with a group number, optionally upload a voice transcript
2. **Analyze** — Click Analyze to send everything to Claude Opus 4.6 Extended Thinking in a single API call
3. **Download Excel** — Download the formatted .xlsx file with 32 columns, formulas, and conditional formatting

---

## Local Development

### Clone the repository
```bash
git clone https://github.com/JvdW123/shelf-analyzer-2.0.git
cd shelf-analyzer-2.0
```

### Install dependencies
```bash
pip install -r requirements.txt
```

### Set up secrets
Create `.streamlit/secrets.toml` with your credentials:
```toml
app_password = "your-password"
anthropic_api_key = "sk-ant-your-api-key"
```

### Run locally
```bash
streamlit run app.py
```

The app will open at `http://localhost:8501`.

---

## Tech Stack

- **Python** — Programming language
- **Streamlit** — Web framework
- **Claude Opus 4.6 Extended Thinking** — AI-powered shelf analysis
- **openpyxl** — Excel file generation and formatting
