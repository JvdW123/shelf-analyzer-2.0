# Changelog — Shelf Analyzer 2.0

All notable changes to this project are documented here.

---

## 2026-02-17 — Phase 5: Production Polish & Deployment
- Added comprehensive error handling and user feedback throughout the app
- Implemented progress indicators for analysis and Excel generation
- Deployed to Streamlit Community Cloud at https://shelf-analyzer-20.streamlit.app/
- Configured secrets via Streamlit Cloud dashboard
- Verified end-to-end workflow in production environment

## 2026-02-17 — Phase 4: Excel Generator
- Built `modules/excel_generator.py` to convert JSON to formatted .xlsx
- Implemented 32-column schema with proper data types
- Added Excel formula for Price per Liter (EUR) calculation
- Applied conditional formatting for Confidence Score (green/yellow/red) and Stock Status (red for out of stock)
- Styled output with alternating row colors, frozen header, and borders
- Wired download button into `app.py` with dynamic filename format

## 2026-02-17 — Phase 3: Claude API Client
- Created `modules/claude_client.py` with Extended Thinking support
- Configured Claude Opus 4.6 with 10,000 thinking tokens and 16,000 max tokens
- Implemented single API call architecture with base64 image encoding
- Added JSON response parsing with error handling
- Integrated Analyze button in `app.py` with status updates

## 2026-02-17 — Phase 2: Analysis Prompt & Builder
- Created `prompts/shelf_analysis.py` with system prompt and analysis prompt template
- Built `modules/prompt_builder.py` to assemble metadata, photo tags, and transcript into complete prompt
- Added prompt preview button in UI for debugging

## 2026-02-17 — Phase 1: Project Skeleton & UI
- Set up folder structure with `modules/` and `prompts/` packages
- Created `config.py` with all settings: dropdowns, retailers by country, exchange rates, column schema, API config
- Built password gate in `app.py` using Streamlit secrets
- Implemented metadata form with dynamic retailer dropdown based on country selection
- Added photo upload with tagging interface (Overview/Close-up + group number)
- Added optional transcript upload (.txt files)

## 2026-02-17 — Phase 0: Foundation
- Created PRD.md (product requirements document)
- Created .cursorrules (AI agent coding instructions)
- Created CHANGELOG.md (this file)
