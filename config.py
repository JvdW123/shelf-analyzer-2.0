"""
Shelf Analyzer 2.0 — Central Configuration File

This file contains ALL settings, dropdown values, and constants used across the app.
No other file should hardcode these values — always import from config.py.
"""

# ==============================================================================
# GEOGRAPHY AND RETAILERS
# ==============================================================================

# List of countries available in the Country dropdown
COUNTRIES = [
    "United Kingdom",
    "France",
    "Germany",
    "Netherlands",
    "Spain",
    "Other"
]

# Dictionary mapping each country to its list of retailers
# Every list ends with "Other" to allow custom retailer input
RETAILERS = {
    "United Kingdom": [
        "Tesco", "Sainsbury's", "Asda", "Morrisons", "Aldi", "Lidl", "Waitrose",
        "M&S", "Co-op", "Iceland", "Ocado", "Spar", "Budgens", "Costcutter",
        "Londis", "Nisa", "One Stop", "Premier", "WHSmith", "Amazon Fresh", "Other"
    ],
    "France": [
        "Carrefour", "E.Leclerc", "Intermarche", "Auchan", "Systeme U", "Lidl",
        "Casino", "Monoprix", "Franprix", "Picard", "Aldi", "Cora", "Grand Frais",
        "Naturalia", "Match", "Colruyt", "Leader Price", "Netto", "Dia", "Biocoop",
        "Other"
    ],
    "Germany": [
        "Edeka", "Rewe", "Aldi Nord", "Aldi Sud", "Lidl", "Kaufland", "Penny",
        "Netto", "Tegut", "Globus", "Famila", "Hit", "Norma", "Combi",
        "Denn's Biomarkt", "Real", "Muller", "Rossmann", "dm", "Wasgau", "Other"
    ],
    "Netherlands": [
        "Albert Heijn", "Jumbo", "Lidl", "Aldi", "Plus", "Dirk", "DekaMarkt",
        "Coop", "Vomar", "Hoogvliet", "Jan Linders", "Spar", "Boni", "Poiesz",
        "Nettorama", "Ekoplaza", "Picnic", "Crisp", "AH to go", "Marqt", "Other"
    ],
    "Spain": [
        "Mercadona", "Carrefour", "Lidl", "Dia", "Eroski", "Alcampo",
        "El Corte Ingles", "Consum", "Bonpreu", "Gadis", "Ahorramas", "Caprabo",
        "Hipercor", "Masymas", "Coviran", "BM Supermercados", "Aldi", "Condis",
        "Spar", "Lupa", "Other"
    ]
}

# ==============================================================================
# STORE AND SHELF ATTRIBUTES
# ==============================================================================

# Store format types available in the dropdown
STORE_FORMATS = [
    "Hypermarket",
    "Supermarket",
    "Convenience Store",
    "Discounter",
    "Express Store",
    "Other"
]

# Shelf location types available in the dropdown
# This value is written into column 7 of every SKU row in the Excel output
SHELF_LOCATIONS = [
    "To-Go Section",
    "Chilled Juice Section",
    "Fresh Produce Department",
    "Checkout Counter",
    "Other"
]

# ==============================================================================
# CURRENCY AND EXCHANGE RATES
# ==============================================================================

# Available currencies for the Currency dropdown
CURRENCIES = ["GBP", "EUR"]

# Exchange rates for currency conversion
# Used to calculate Price (EUR) from Price (Local Currency)
EXCHANGE_RATES = {
    "GBP_TO_EUR": 1.17
}

# ==============================================================================
# PHOTO TAGGING
# ==============================================================================

# Photo type options for tagging uploaded images
PHOTO_TYPES = ["Overview", "Close-up"]

# ==============================================================================
# CLAUDE API CONFIGURATION
# ==============================================================================

# Settings for Claude Opus 4.6 Extended Thinking API calls
CLAUDE_CONFIG = {
    "model": "claude-opus-4-6",
    "max_tokens": 64000,  # Maximum capacity - handles 140+ SKUs
    "thinking": {
        "type": "enabled",
        "budget_tokens": 10000  # Balanced thinking for good speed and accuracy
    }
}

# ==============================================================================
# DATA SCHEMA — 32 COLUMNS
# ==============================================================================

# Complete column specification for Excel output
# Each dictionary defines one column with:
#   - name: Display name for Excel header
#   - key: JSON key from Claude's response
#   - type: Data type ("text", "integer", or "float")
# Order matters — this is the exact order columns appear in the Excel file
COLUMN_SCHEMA = [
    {"name": "Country", "key": "country", "type": "text"},
    {"name": "City", "key": "city", "type": "text"},
    {"name": "Retailer", "key": "retailer", "type": "text"},
    {"name": "Store Format", "key": "store_format", "type": "text"},
    {"name": "Store Name", "key": "store_name", "type": "text"},
    {"name": "Photo", "key": "photo", "type": "text"},
    {"name": "Shelf Location", "key": "shelf_location", "type": "text"},
    {"name": "Shelf Levels", "key": "shelf_levels", "type": "integer"},
    {"name": "Shelf Level", "key": "shelf_level", "type": "text"},
    {"name": "Product Type", "key": "product_type", "type": "text"},
    {"name": "Branded/Private Label", "key": "branded_private_label", "type": "text"},
    {"name": "Brand", "key": "brand", "type": "text"},
    {"name": "Sub-brand", "key": "sub_brand", "type": "text"},
    {"name": "Product Name", "key": "product_name", "type": "text"},
    {"name": "Flavor", "key": "flavor", "type": "text"},
    {"name": "Facings", "key": "facings", "type": "integer"},
    {"name": "Price (Local Currency)", "key": "price_local", "type": "float"},
    {"name": "Currency", "key": "currency", "type": "text"},
    {"name": "Price (EUR)", "key": "price_eur", "type": "float"},
    {"name": "Packaging Size (ml)", "key": "packaging_size_ml", "type": "integer"},
    {"name": "Price per Liter (EUR)", "key": "price_per_liter_eur", "type": "float"},
    {"name": "Need State", "key": "need_state", "type": "text"},
    {"name": "Juice Extraction Method", "key": "juice_extraction_method", "type": "text"},
    {"name": "Processing Method", "key": "processing_method", "type": "text"},
    {"name": "HPP Treatment", "key": "hpp_treatment", "type": "text"},
    {"name": "Packaging Type", "key": "packaging_type", "type": "text"},
    {"name": "Claims", "key": "claims", "type": "text"},
    {"name": "Bonus/Promotions", "key": "bonus_promotions", "type": "text"},
    {"name": "Stock Status", "key": "stock_status", "type": "text"},
    {"name": "Est. Linear Meters", "key": "est_linear_meters", "type": "float"},
    {"name": "Fridge Number", "key": "fridge_number", "type": "text"},
    {"name": "Confidence Score", "key": "confidence_score", "type": "integer"}
]

# ==============================================================================
# EXCEL FORMATTING CONFIGURATION
# ==============================================================================

# Settings for Excel output styling and formatting
EXCEL_CONFIG = {
    # Sheet properties
    "sheet_name": "SKU Data",
    
    # Font settings
    "font_name": "Arial",
    "font_size": 10,
    
    # Header row styling
    "header_bg_color": "2F5496",
    "header_font_color": "FFFFFF",
    
    # Data row styling
    "alt_row_color": "F2F2F2",
    "header_row_height": 22.5,
    "data_row_height": 15,
    
    # Conditional formatting for Confidence Score (column 32)
    "confidence_high": {
        "min": 75,
        "bg": "C6EFCE",
        "font": "006100"
    },
    "confidence_mid": {
        "min": 55,
        "bg": "FFEB9C",
        "font": "9C6500"
    },
    "confidence_low": {
        "bg": "FFC7CE",
        "font": "9C0006"
    },
    
    # Conditional formatting for Stock Status (column 29)
    "out_of_stock": {
        "bg": "FFC7CE",
        "font": "9C0006"
    }
}
