# Shelf Analyzer 2.0

A web application that converts supermarket shelf photos into structured Excel reports using AI-powered analysis.

## Setup Instructions

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Configure Secrets
Create or edit `.streamlit/secrets.toml` with your credentials:
```toml
app_password = "your-password"
anthropic_api_key = "sk-ant-your-api-key"
```

### 3. Run the Application
```bash
streamlit run app.py
```

The app will open in your browser at `http://localhost:8501`.
