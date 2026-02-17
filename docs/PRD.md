# Shelf Analyzer 2.0 — Product Requirements Document (PRD)

**Version:** 1.2  
**Last Updated:** 2026-02-17  
**Author:** Jurjen  
**Status:** In Development

---

## 1. Product Overview

### What It Does
Shelf Analyzer 2.0 is a web application that converts supermarket shelf photos into structured Excel reports. Users upload photos of juice/smoothie shelves, the tool sends them to Claude Opus 4.6 with Extended Thinking for AI-powered analysis, and outputs a formatted Excel file with one row per unique SKU (Stock Keeping Unit — a single distinct product).

### Who Uses It
Colleagues at Fruity Line (juice and smoothie company) who conduct store visit analyses across European retailers. The tool supports market positioning analysis, private label vs. branded splits, and category performance insights.

### The 3-Step Workflow
1. **Upload and Tag** — User enters store metadata (country, city, retailer, store format, store name, shelf location, currency), uploads shelf photos, tags each as Overview or Close-up with a group number, optionally uploads a voice transcript (.txt)
2. **Analyze** — ALL photos + ONE prompt + metadata + transcript are sent to Claude Opus 4.6 Extended Thinking in a SINGLE API call — Claude returns ONE JSON array of SKUs
3. **Download** — Python converts the JSON into a formatted .xlsx file with 32 columns, formulas, and conditional formatting

### Critical Design Principle: Simplicity
This tool must stay simple. The entire analysis happens in ONE prompt, ONE API call, ONE response. There is no multi-step prompting, no chaining, no loops. Claude receives everything at once and returns everything at once.

```
User fills form + uploads photos + optional transcript
                    |
                    v
    Python assembles ONE prompt with everything
                    |
                    v
      ONE API call to Claude Opus 4.6 Extended Thinking
                    |
                    v
        Claude returns ONE JSON array
                    |
                    v
       Python converts JSON to formatted Excel
                    |
                    v
            User downloads Excel
```

---

## 2. Architecture

```
shelf-analyzer-2.0/
├── app.py                      # Streamlit UI (upload, tag, metadata, submit, download)
├── config.py                   # All settings: dropdowns, retailers, exchange rates, API config
├── modules/
│   ├── __init__.py             # Empty file — makes this folder a Python package
│   ├── claude_client.py        # Sends photos + prompt to Claude API, returns parsed JSON
│   ├── prompt_builder.py       # Assembles the full prompt with metadata + photo tags
│   └── excel_generator.py      # JSON → formatted .xlsx with formulas and styling
├── prompts/
│   ├── __init__.py             # Empty file — makes this folder a Python package
│   └── shelf_analysis.py       # The full analysis prompt as a Python string
├── docs/
│   └── PRD.md                  # This file — product requirements
├── .cursorrules                # Cursor AI agent instructions (auto-read by agent)
├── .streamlit/
│   └── secrets.toml            # API key + app password (local only, never committed)
├── requirements.txt            # Python packages: streamlit, anthropic, openpyxl
├── .env.example                # Template showing required secrets
├── .gitignore                  # Keeps secrets and cache out of Git
├── CHANGELOG.md                # Log of what changed and when
└── README.md                   # Setup instructions for new users
```

### File Responsibilities (one job per file)

| File | Single Responsibility |
|------|----------------------|
| `app.py` | UI only — layout, forms, buttons, user interaction |
| `config.py` | All settings — dropdowns, exchange rates, column schema, API config |
| `modules/claude_client.py` | API communication — send ONE request, receive ONE response, parse JSON |
| `modules/prompt_builder.py` | Prompt assembly — plug metadata into prompt template |
| `modules/excel_generator.py` | Excel creation — JSON to formatted .xlsx |
| `prompts/shelf_analysis.py` | Prompt text — the actual instructions sent to Claude |

---

## 3. Tech Stack

| Technology | Purpose | Version |
|-----------|---------|---------|
| Python | Programming language | 3.11+ |
| Streamlit | Web framework for the UI | Latest |
| anthropic | Official Python SDK for Claude API | Latest |
| openpyxl | Excel file creation and formatting | Latest |
| Claude Opus 4.6 Extended Thinking | AI model for shelf analysis | claude-opus-4-6 |

### Dependencies (requirements.txt)
```
streamlit
anthropic
openpyxl
```

---

## 4. Claude API Configuration

| Setting | Value |
|---------|-------|
| Model | `claude-opus-4-6` |
| Extended Thinking | `thinking: {"type": "enabled", "budget_tokens": 10000}` |
| Max tokens | 16000 |
| Image format | Base64-encoded content blocks |
| System prompt | Defined in `prompts/shelf_analysis.py` as `SYSTEM_PROMPT` |
| User message | Built by `modules/prompt_builder.py` using `ANALYSIS_PROMPT` template |
| API calls per analysis | Exactly ONE — all photos + prompt sent together |

### How Extended Thinking Works
Extended Thinking lets Claude "think out loud" before responding. It uses a thinking budget (tokens allocated for reasoning) before producing the final output. This is critical for shelf analysis because Claude needs to cross-reference photos, count facings, deduplicate SKUs, and verify prices — all complex reasoning tasks.

### Response Handling
- Claude's response contains both `thinking` blocks and `text` blocks
- Skip all thinking blocks — extract only text blocks
- Parse the text content as a JSON array
- Each element in the array = one SKU row

---

## 5. UI Specification

### 5.1 Password Gate
- Password stored in `.streamlit/secrets.toml` under key `app_password`
- User sees a centered login screen with a password input field
- On correct password, the full app loads
- On incorrect password, show error message

### 5.2 Metadata Form
All metadata fields appear before the photo upload section. These are filled in by the user and passed to Claude as context AND written into the Excel output.

**Country** — dropdown:
- United Kingdom, France, Germany, Netherlands, Spain, Other
- If "Other" selected, show free text input

**City** — free text input

**Retailer** — dynamic dropdown that changes based on selected country:
- **United Kingdom:** Tesco, Sainsbury's, Asda, Morrisons, Aldi, Lidl, Waitrose, M&S, Co-op, Iceland, Ocado, Spar, Budgens, Costcutter, Londis, Nisa, One Stop, Premier, WHSmith, Amazon Fresh, Other
- **France:** Carrefour, E.Leclerc, Intermarche, Auchan, Systeme U, Lidl, Casino, Monoprix, Franprix, Picard, Aldi, Cora, Grand Frais, Naturalia, Match, Colruyt, Leader Price, Netto, Dia, Biocoop, Other
- **Germany:** Edeka, Rewe, Aldi Nord, Aldi Sud, Lidl, Kaufland, Penny, Netto, Tegut, Globus, Famila, Hit, Norma, Combi, Denn's Biomarkt, Real, Muller, Rossmann, dm, Wasgau, Other
- **Netherlands:** Albert Heijn, Jumbo, Lidl, Aldi, Plus, Dirk, DekaMarkt, Coop, Vomar, Hoogvliet, Jan Linders, Spar, Boni, Poiesz, Nettorama, Ekoplaza, Picnic, Crisp, AH to go, Marqt, Other
- **Spain:** Mercadona, Carrefour, Lidl, Dia, Eroski, Alcampo, El Corte Ingles, Consum, Bonpreu, Gadis, Ahorramas, Caprabo, Hipercor, Masymas, Coviran, BM Supermercados, Aldi, Condis, Spar, Lupa, Other
- If "Other" selected, show free text input

**Store Format** — dropdown:
- Hypermarket, Supermarket, Convenience Store, Discounter, Express Store, Other
- If "Other" selected, show free text input

**Store Name** — free text input

**Shelf Location** — dropdown:
- To-Go Section, Chilled Juice Section, Fresh Produce Department, Checkout Counter, Other
- If "Other" selected, show free text input
- This value is written into column 7 ("Shelf Location") of every SKU row in the Excel output

**Currency** — dropdown: GBP, EUR

**Exchange rate:** GBP to EUR = 1.17 (hardcoded in `config.py`, easy to update)

### 5.3 Photo Upload and Tagging
- File uploader accepts multiple image files (jpg, jpeg, png)
- After upload, each photo is displayed with:
  - A thumbnail preview of the image
  - Dropdown: "Overview" or "Close-up"
  - Number input: Group (1, 2, 3...) — photos with the same group belong to the same fridge/shelf
- Example grouping for a store with 3 fridges:
  ```
  foto_1.jpg    -> Overview  | Group 1
  foto_1a.jpg   -> Close-up  | Group 1
  foto_1b.jpg   -> Close-up  | Group 1
  foto_2.jpg    -> Overview  | Group 2
  foto_2a.jpg   -> Close-up  | Group 2
  foto_3.jpg    -> Overview  | Group 3
  foto_3a.jpg   -> Close-up  | Group 3
  ```

### 5.4 Transcript Upload
- Optional file uploader for a single .txt file
- The transcript contains a voice description of the shelf
- If uploaded, its content is passed to Claude as supplementary context

### 5.5 Analyze Button
- Disabled until at least one photo is uploaded and all required metadata is filled
- On click: shows a progress spinner with status messages
- Triggers exactly ONE API call to Claude
- After completion: displays the number of SKUs found

### 5.6 Download Button
- Appears only after successful analysis
- Downloads the formatted .xlsx file
- Filename format: `{Retailer}_{City}_{YYYY-MM-DD}.xlsx` (e.g., `Tesco_London_2026-02-17.xlsx`)

---

## 6. Data Schema — 32 Columns

### 6.1 Complete Column Specification

| # | Column | JSON Key | Type | Source | Allowed Values |
|---|--------|----------|------|--------|----------------|
| 1 | Country | country | text | Metadata (user input) | Free text |
| 2 | City | city | text | Metadata (user input) | Free text |
| 3 | Retailer | retailer | text | Metadata (user input) | Free text |
| 4 | Store Format | store_format | text | Metadata (user input) | FIXED: Hypermarket / Supermarket / Convenience Store / Discounter / Express Store / Other |
| 5 | Store Name | store_name | text | Metadata (user input) | Free text |
| 6 | Photo | photo | text | Filename | Exact filename |
| 7 | Shelf Location | shelf_location | text | Metadata (user input) | FIXED: To-Go Section / Chilled Juice Section / Fresh Produce Department / Checkout Counter / Other |
| 8 | Shelf Levels | shelf_levels | integer | AI analysis | Numeric |
| 9 | Shelf Level | shelf_level | text | AI analysis | FIXED: 1st / 2nd / 3rd / 4th / 5th / 6th |
| 10 | Product Type | product_type | text | AI analysis | FIXED: Pure Juices / Smoothies / Shots / Other |
| 11 | Branded/Private Label | branded_private_label | text | AI analysis | FIXED: Branded / Private Label |
| 12 | Brand | brand | text | AI analysis | Free text |
| 13 | Sub-brand | sub_brand | text | AI analysis | Free text |
| 14 | Product Name | product_name | text | AI analysis | Free text |
| 15 | Flavor | flavor | text | AI analysis | Free text |
| 16 | Facings | facings | integer | AI analysis | Numeric |
| 17 | Price (Local Currency) | price_local | float | AI analysis | Numeric (null if not visible) |
| 18 | Currency | currency | text | Metadata (user input) | FIXED: GBP / EUR |
| 19 | Price (EUR) | price_eur | float | Calculated | Numeric (null if no local price) |
| 20 | Packaging Size (ml) | packaging_size_ml | integer | AI analysis | Numeric (null if not visible) |
| 21 | Price per Liter (EUR) | price_per_liter_eur | float | Excel formula | null in JSON — Excel formula in output |
| 22 | Need State | need_state | text | AI analysis | FIXED: Indulgence / Functional |
| 23 | Juice Extraction Method | juice_extraction_method | text | AI analysis | FIXED: Squeezed / Cold Pressed / From Concentrate (null if unknown) |
| 24 | Processing Method | processing_method | text | AI analysis | FIXED: Pasteurized / HPP (null if unknown) |
| 25 | HPP Treatment | hpp_treatment | text | AI analysis | FIXED: Yes / No (null if unknown) |
| 26 | Packaging Type | packaging_type | text | AI analysis | FIXED: PET Bottle / Tetra Pak / Can / Carton / Glass Bottle |
| 27 | Claims | claims | text | AI analysis | Free text, comma-separated (null if none) |
| 28 | Bonus/Promotions | bonus_promotions | text | AI analysis | Free text (null if none) |
| 29 | Stock Status | stock_status | text | AI analysis | FIXED: In Stock / Out of Stock |
| 30 | Est. Linear Meters | est_linear_meters | float | AI analysis | Numeric |
| 31 | Fridge Number | fridge_number | text | AI analysis | Free text |
| 32 | Confidence Score | confidence_score | integer | AI analysis | 0-100 |

### 6.2 Metadata vs. AI Columns
Some columns are filled by the USER (from the metadata form), others by CLAUDE (from photo analysis):

**User-provided (same value for every row):**
- Columns 1-5: Country, City, Retailer, Store Format, Store Name
- Column 7: Shelf Location
- Column 18: Currency

**Claude-provided (different per SKU):**
- Column 6: Photo (filename)
- Columns 8-17: Shelf details, product info, facings, price
- Columns 19-32: Calculated values, packaging, claims, scoring

**Special:**
- Column 19 (Price EUR): Calculated by Claude using exchange rate from metadata
- Column 21 (Price per Liter EUR): Always null in JSON — calculated as Excel formula in output

### 6.3 Fixed Value Reference
```
Store Format:             Hypermarket, Supermarket, Convenience Store, Discounter, Express Store, Other
Shelf Location:           To-Go Section, Chilled Juice Section, Fresh Produce Department, Checkout Counter, Other
Shelf Level:              1st, 2nd, 3rd, 4th, 5th, 6th
Product Type:             Pure Juices, Smoothies, Shots, Other
Branded/Private Label:    Branded, Private Label
Currency:                 GBP, EUR
Need State:               Indulgence, Functional
Juice Extraction Method:  Squeezed, Cold Pressed, From Concentrate
Processing Method:        Pasteurized, HPP
HPP Treatment:            Yes, No
Packaging Type:           PET Bottle, Tetra Pak, Can, Carton, Glass Bottle
Stock Status:             In Stock, Out of Stock
```

---

## 7. Excel Output Formatting

### 7.1 General
- Sheet name: "SKU Data"
- Font: Arial 10pt throughout
- Text wrapping: disabled
- Frozen header row (row 1 stays visible when scrolling)

### 7.2 Header Row
- Background: dark blue (#2F5496)
- Text: white, bold
- Row height: approximately 22.5pt

### 7.3 Data Rows
- Alternating row shading: light grey (#F2F2F2) and white (#FFFFFF)
- Row height: approximately 15pt
- Thin borders on all cells

### 7.4 Column 21 — Price per Liter (EUR)
- Must be an Excel FORMULA, not a hardcoded value
- Formula: `=IFERROR(S{row}/(T{row}/1000),"")`
- Where S = Price (EUR) column, T = Packaging Size (ml) column
- IFERROR wraps it so blank/zero values show empty instead of #DIV/0!

### 7.5 Conditional Formatting
**Confidence Score (column 32):**
- 75 or above: green fill (#C6EFCE) with dark green text (#006100)
- 55 to 74: yellow fill (#FFEB9C) with dark yellow text (#9C6500)
- Below 55: red fill (#FFC7CE) with dark red text (#9C0006)

**Stock Status (column 29):**
- "Out of Stock": red fill (#FFC7CE) with bold red text (#9C0006)

### 7.6 Output Filename
Format: `{Retailer}_{City}_{YYYY-MM-DD}.xlsx`
Example: `Tesco_London_2026-02-17.xlsx`

---

## 8. Prompt System

### 8.1 File: prompts/shelf_analysis.py
Contains two string variables:
- `SYSTEM_PROMPT` — sets Claude's role as an expert retail shelf analyst
- `ANALYSIS_PROMPT` — the full 5-step analysis instructions with three placeholders:
  - `{metadata_block}` — store metadata (country, city, retailer, shelf location, etc.)
  - `{photo_list_block}` — list of photos with their tags (type + group)
  - `{transcript_block}` — transcript text (or empty if not provided)

### 8.2 File: modules/prompt_builder.py
Takes user inputs and fills in the prompt template:
- Builds the metadata block from form values (including shelf location)
- Builds the photo list block from uploaded files and their tags
- Inserts transcript text if provided
- Returns the complete prompt string ready to send to Claude

### 8.3 Single-Prompt Design
The prompt builder produces ONE complete prompt. The claude_client sends it in ONE API call. Claude processes everything at once and returns ONE JSON array. There is no multi-step prompting.

---

## 9. Security

- **App password** stored in `.streamlit/secrets.toml` (key: `app_password`)
- **API key** stored in `.streamlit/secrets.toml` (key: `anthropic_api_key`)
- `.streamlit/secrets.toml` is in `.gitignore` — never committed to Git
- `.env.example` shows the required keys without actual values
- On Streamlit Cloud: secrets are configured via the dashboard (Settings > Secrets)

---

## 10. Deployment

- **Platform:** Streamlit Community Cloud (free tier)
- **Repository:** GitHub (github.com/JvdW123/shelf-analyzer-2.0)
- **Branch strategy:** `dev` for building, `main` for production deployment
- Streamlit Cloud auto-deploys from `main` branch

---

## 11. Build Phases

### Phase 0: Foundation Documents
- [x] PRD.md (this file)
- [ ] .cursorrules
- [ ] CHANGELOG.md

### Phase 1: Project Setup + UI
- [ ] Step 1.1: Folder structure + empty files + requirements.txt + .gitignore
- [ ] Step 1.2: config.py (all settings and dropdowns)
- [ ] Step 1.3: app.py part 1 (password gate + metadata form)
- [ ] Step 1.4: app.py part 2 (photo upload + tagging + transcript)

### Phase 2: Prompt Builder
- [ ] Step 2.1: prompts/shelf_analysis.py (paste existing prompt)
- [ ] Step 2.2: modules/prompt_builder.py + preview button

### Phase 3: Claude API Connection
- [ ] Step 3.1: modules/claude_client.py (single API call)
- [ ] Step 3.2: Wire into app.py (Analyze button)

### Phase 4: Excel Generator
- [ ] Step 4.1: modules/excel_generator.py
- [ ] Step 4.2: Wire download button into app.py

### Phase 5: Polish + Deploy
- [ ] Step 5.1: Error handling + progress indicators
- [ ] Step 5.2: Git + GitHub + Streamlit Cloud deploy
