"""
pages/99_Accuracy_Tester.py

Developer Tool — Accuracy Testing

NOT part of the live user-facing app.
This page lets a developer:
  1. Upload shelf photos for a single store visit
  2. Upload a manually verified ground-truth Excel file
  3. Run the existing analysis pipeline on the photos to produce a new Excel
  4. Compare the generated Excel against the ground truth at the field level
  5. View per-column accuracy scores and an error table
  6. Trigger a Claude diagnostic (Quick = Sonnet, Deep = Opus + Extended Thinking)

The comparison step is 100% pure Python — no LLM calls involved.
Diagnostic LLM calls are triggered only by explicit button clicks.
"""

import io
import json
import traceback

import pandas as pd
import streamlit as st
from PIL import Image

# ---------------------------------------------------------------------------
# Page config — must be the very first Streamlit call
# ---------------------------------------------------------------------------

st.set_page_config(
    page_title="Accuracy Tester — Dev Tool",
    page_icon="🔬",
    layout="wide",
)

# ---------------------------------------------------------------------------
# Password gate (same mechanism as main app.py)
# ---------------------------------------------------------------------------

if "at_authenticated" not in st.session_state:
    st.session_state["at_authenticated"] = False

if not st.session_state["at_authenticated"]:
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.title("Accuracy Tester")
        st.caption("Developer tool — password required")
        pw = st.text_input("Password", type="password", key="at_pw_field")
        if st.button("Login", type="primary", use_container_width=True):
            if pw == st.secrets["app_password"]:
                st.session_state["at_authenticated"] = True
                st.rerun()
            else:
                st.error("Incorrect password")
    st.stop()

# ---------------------------------------------------------------------------
# Header
# ---------------------------------------------------------------------------

st.title("Developer Tool — Accuracy Testing")
st.caption(
    "Compare pipeline output against a manually verified ground-truth Excel. "
    "This tool is for development diagnostics only and is not visible to end users."
)
st.divider()

# ---------------------------------------------------------------------------
# Import project modules (after page config)
# ---------------------------------------------------------------------------

from config import COUNTRIES, RETAILERS, STORE_FORMATS, SHELF_LOCATIONS, CURRENCIES, PHOTO_TYPES
from config import EXCHANGE_RATES
from modules.prompt_builder import build_prompt
from modules.claude_client import analyze_shelf
from modules.excel_generator import generate_excel
from prompts.shelf_analysis import SYSTEM_PROMPT
from accuracy_tester.excel_reader import read_excel
from accuracy_tester.semantic_scorer import run_semantic_scoring
from accuracy_tester.scorer import get_flagged_table

# ---------------------------------------------------------------------------
# Session state initialisation
# ---------------------------------------------------------------------------

_state_defaults = {
    "at_photo_tags": [],
    "at_transcript_text": None,
    "at_generated_skus": None,
    "at_generated_excel_bytes": None,
    "at_semantic_result": None,
    "at_metadata": None,
    "at_diagnosis_text": None,
    "at_diagnosis_mode": None,
}
for k, v in _state_defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v

# ---------------------------------------------------------------------------
# SECTION 1 — Metadata form
# ---------------------------------------------------------------------------

st.header("1. Store Metadata")
st.caption("Same fields as the main tool — used to run the analysis pipeline.")

col1, col2 = st.columns(2)
with col1:
    at_country = st.selectbox("Country", COUNTRIES, key="at_country")
with col2:
    at_city = st.text_input("City", key="at_city")

col1, col2 = st.columns(2)
with col1:
    if at_country == "Other" or at_country not in RETAILERS:
        retailer_opts = ["Other"]
    else:
        retailer_opts = RETAILERS[at_country]
    at_retailer = st.selectbox("Retailer", retailer_opts, key="at_retailer")
    if at_retailer == "Other":
        at_retailer_other = st.text_input("Specify Retailer", key="at_retailer_other")
    else:
        at_retailer_other = ""
with col2:
    at_store_format = st.selectbox("Store Format", STORE_FORMATS, key="at_store_format")
    if at_store_format == "Other":
        at_store_format_other = st.text_input("Specify Store Format", key="at_store_format_other")
    else:
        at_store_format_other = ""

col1, col2 = st.columns(2)
with col1:
    at_store_name = st.text_input("Store Name", key="at_store_name")
with col2:
    at_shelf_location = st.selectbox("Shelf Location", SHELF_LOCATIONS, key="at_shelf_location")
    if at_shelf_location == "Other":
        at_shelf_location_other = st.text_input("Specify Shelf Location", key="at_shelf_location_other")
    else:
        at_shelf_location_other = ""

at_currency = st.selectbox("Currency", CURRENCIES, key="at_currency")

# ---------------------------------------------------------------------------
# SECTION 2 — Photo upload and tagging
# ---------------------------------------------------------------------------

st.divider()
st.header("2. Shelf Photos")
st.caption("Upload the photos for this store visit. These will be sent to the analysis pipeline.")

at_uploaded_photos = st.file_uploader(
    "Upload shelf photos",
    type=["jpg", "jpeg", "png"],
    accept_multiple_files=True,
    key="at_photo_uploader",
)

if at_uploaded_photos:
    photo_tags = []
    for i, photo in enumerate(at_uploaded_photos):
        rot_key = f"at_rotation_{i}"
        if rot_key not in st.session_state:
            st.session_state[rot_key] = 0

        img = Image.open(io.BytesIO(photo.getvalue()))
        angle = st.session_state[rot_key]
        if angle != 0:
            img = img.rotate(-angle, expand=True)

        col_img, _ = st.columns(2)
        with col_img:
            preview_buf = io.BytesIO()
            img.convert("RGB").save(preview_buf, format="JPEG")
            st.image(preview_buf.getvalue(), use_container_width=True)

            ctrl_rot, ctrl_type, ctrl_group = st.columns([1, 2, 1])
            with ctrl_rot:
                r1, r2 = st.columns(2)
                with r1:
                    if st.button("\u21BA", key=f"at_rot_ccw_{i}", help="Rotate CCW"):
                        st.session_state[rot_key] = (st.session_state[rot_key] - 90) % 360
                        st.rerun()
                with r2:
                    if st.button("\u21BB", key=f"at_rot_cw_{i}", help="Rotate CW"):
                        st.session_state[rot_key] = (st.session_state[rot_key] + 90) % 360
                        st.rerun()
            with ctrl_type:
                photo_type = st.selectbox(
                    "Photo Type", PHOTO_TYPES,
                    key=f"at_type_{i}",
                )
            with ctrl_group:
                group_number = st.number_input(
                    "Group", min_value=1, value=1, step=1,
                    key=f"at_group_{i}",
                )

        st.divider()

        rotated_buf = io.BytesIO()
        img.convert("RGB").save(rotated_buf, format="JPEG", quality=95)
        photo_tags.append({
            "filename": photo.name,
            "type": photo_type,
            "group": group_number,
            "data": rotated_buf.getvalue(),
        })

    st.session_state["at_photo_tags"] = photo_tags

# Optional transcript
st.divider()
st.subheader("Transcript (Optional)")
at_transcript_file = st.file_uploader(
    "Upload voice transcript (.txt)", type=["txt"], key="at_transcript_uploader"
)
if at_transcript_file:
    st.session_state["at_transcript_text"] = at_transcript_file.read().decode("utf-8")
    st.success(f"Transcript loaded ({len(st.session_state['at_transcript_text'])} chars)")
else:
    st.session_state["at_transcript_text"] = None

# ---------------------------------------------------------------------------
# SECTION 3 — Ground truth upload
# ---------------------------------------------------------------------------

st.divider()
st.header("3. Ground Truth Excel")
st.caption(
    "Upload the manually verified .xlsx file for this store visit. "
    "This is your 100% accurate reference."
)

at_ground_truth_file = st.file_uploader(
    "Upload ground truth Excel (.xlsx)",
    type=["xlsx"],
    key="at_gt_uploader",
)

# ---------------------------------------------------------------------------
# SECTION 4 — Run pipeline
# ---------------------------------------------------------------------------

st.divider()
st.header("4. Run Analysis Pipeline")

# Validation
photos_ready = len(st.session_state.get("at_photo_tags", [])) > 0
gt_ready = at_ground_truth_file is not None
city_ready = st.session_state.get("at_city", "").strip() != ""
store_name_ready = st.session_state.get("at_store_name", "").strip() != ""
retailer_val = st.session_state.get("at_retailer", "")
if retailer_val == "Other":
    retailer_ready = st.session_state.get("at_retailer_other", "").strip() != ""
else:
    retailer_ready = bool(retailer_val)

can_run = photos_ready and gt_ready and city_ready and store_name_ready and retailer_ready

if not can_run:
    missing = []
    if not photos_ready:
        missing.append("shelf photos")
    if not gt_ready:
        missing.append("ground truth Excel")
    if not city_ready:
        missing.append("city")
    if not store_name_ready:
        missing.append("store name")
    if not retailer_ready:
        missing.append("retailer")
    st.info(f"Still needed: {', '.join(missing)}")

if st.button(
    "Run Pipeline + Compare",
    disabled=not can_run,
    type="primary",
):
    # Build metadata
    final_retailer = (
        st.session_state.get("at_retailer_other", "")
        if st.session_state.get("at_retailer") == "Other"
        else st.session_state.get("at_retailer", "")
    )
    final_store_format = (
        st.session_state.get("at_store_format_other", "")
        if st.session_state.get("at_store_format") == "Other"
        else st.session_state.get("at_store_format", "")
    )
    final_shelf_location = (
        st.session_state.get("at_shelf_location_other", "")
        if st.session_state.get("at_shelf_location") == "Other"
        else st.session_state.get("at_shelf_location", "")
    )

    metadata = {
        "country": st.session_state.get("at_country", ""),
        "city": st.session_state.get("at_city", ""),
        "retailer": final_retailer,
        "store_format": final_store_format,
        "store_name": st.session_state.get("at_store_name", ""),
        "shelf_location": final_shelf_location,
        "currency": st.session_state.get("at_currency", ""),
        "exchange_rate": EXCHANGE_RATES["GBP_TO_EUR"],
    }
    st.session_state["at_metadata"] = metadata

    with st.status("Running accuracy test...", expanded=True) as status:
        try:
            # Step 1: Read ground truth
            st.write("Step 1: Reading ground truth Excel...")
            gt_rows = read_excel(at_ground_truth_file.getvalue())
            st.write(f"  → {len(gt_rows)} rows in ground truth")

            # Step 2: Run the analysis pipeline
            st.write("Step 2: Sending photos to Claude (this may take 1–3 minutes)...")
            photo_tags_for_prompt = [
                {"filename": t["filename"], "type": t["type"], "group": t["group"]}
                for t in st.session_state["at_photo_tags"]
            ]
            user_prompt = build_prompt(
                metadata=metadata,
                photo_tags=photo_tags_for_prompt,
                transcript_text=st.session_state["at_transcript_text"],
            )
            api_result = analyze_shelf(
                system_prompt=SYSTEM_PROMPT,
                user_prompt=user_prompt,
                photos=st.session_state["at_photo_tags"],
            )
            skus = api_result["skus"]
            st.write(f"  → Pipeline returned {len(skus)} SKUs")
            st.session_state["at_generated_skus"] = skus

            # Step 3: Generate Excel from pipeline output
            st.write("Step 3: Generating Excel from pipeline output...")
            meta_for_excel = {k: v for k, v in metadata.items() if k != "exchange_rate"}
            excel_bytes = generate_excel(skus, meta_for_excel)
            st.session_state["at_generated_excel_bytes"] = excel_bytes

            # Step 4: Read generated Excel back through the same normaliser
            st.write("Step 4: Normalising generated Excel for comparison...")
            gen_rows = read_excel(excel_bytes)

            # Step 5: Semantic scoring via Claude Opus Extended Thinking
            st.write(
                "Step 5: Running semantic scoring via Claude Opus "
                "(Extended Thinking) — this may take 2–4 minutes..."
            )
            semantic_result = run_semantic_scoring(
                gt_rows=gt_rows,
                gen_rows=gen_rows,
                api_key=st.secrets["anthropic_api_key"],
            )
            st.session_state["at_semantic_result"] = semantic_result
            st.session_state["at_diagnosis_text"] = None  # reset narrative

            s1 = semantic_result["section1"]
            status.update(
                label=(
                    f"Done! Completeness: {s1['completeness_score_pct']:.1f}% — "
                    f"{s1['matched_count']}/{s1['total_gt_count']} SKUs matched"
                ),
                state="complete",
                expanded=False,
            )

        except Exception as e:
            status.update(label=f"Error: {type(e).__name__}", state="error", expanded=True)
            st.error(str(e))
            with st.expander("Traceback"):
                st.code(traceback.format_exc())

# ---------------------------------------------------------------------------
# SECTION 5 — Results (6 sections)
# ---------------------------------------------------------------------------

if st.session_state.get("at_semantic_result") is not None:
    result = st.session_state["at_semantic_result"]

    st.divider()
    st.header("5. Accuracy Results")

    # --- Download buttons ---
    if st.session_state.get("at_generated_excel_bytes"):
        dl_col1, dl_col2, _ = st.columns([1, 1, 2])
        with dl_col1:
            st.download_button(
                label="Download Generated Excel",
                data=st.session_state["at_generated_excel_bytes"],
                file_name="generated_output.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
        with dl_col2:
            if at_ground_truth_file is not None:
                st.download_button(
                    label="Re-download Ground Truth",
                    data=at_ground_truth_file.getvalue(),
                    file_name="ground_truth.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                )

    st.write("")

    # Shared colour helper (used by sections 2, 3, 4)
    def _colour_pct(val):
        if not isinstance(val, (int, float)):
            return ""
        if val >= 90:
            return "background-color: #C6EFCE; color: #006100"
        elif val >= 70:
            return "background-color: #FFEB9C; color: #9C6500"
        return "background-color: #FFC7CE; color: #9C0006"

    # -----------------------------------------------------------------------
    # Section 1 — Completeness Score
    # -----------------------------------------------------------------------
    st.subheader("Section 1 — Completeness Score")
    s1 = result["section1"]

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Completeness Score", f"{s1['completeness_score_pct']:.1f}%")
    c2.metric("Matched SKUs", s1["matched_count"])
    c3.metric("Missed SKUs", len(s1["missed_skus"]))
    c4.metric("Hallucinated SKUs", len(s1["hallucinated_skus"]))

    if s1["missed_skus"]:
        with st.expander(
            f"Missed SKUs ({len(s1['missed_skus'])}) — in ground truth but NOT found by pipeline"
        ):
            st.dataframe(
                pd.DataFrame(s1["missed_skus"]),
                use_container_width=True,
                hide_index=True,
            )

    if s1["hallucinated_skus"]:
        with st.expander(
            f"Hallucinated SKUs ({len(s1['hallucinated_skus'])}) — found by pipeline but NOT in ground truth"
        ):
            st.dataframe(
                pd.DataFrame(s1["hallucinated_skus"]),
                use_container_width=True,
                hide_index=True,
            )

    # -----------------------------------------------------------------------
    # Section 2 — Critical Field Accuracy
    # -----------------------------------------------------------------------
    st.subheader("Section 2 — Critical Field Accuracy")
    s2 = result["section2"]

    _s2_labels = {
        "shelf_level":            "Shelf Level",
        "number_of_shelf_levels": "Number of Shelf Levels",
        "facings":                "Facings",
        "price":                  "Price (Local, ±0.01 tolerance)",
        "packaging_size_ml":      "Packaging Size (ml)",
    }
    s2_rows = [
        {
            "Field": _s2_labels.get(k, k),
            "Correct": v["correct"],
            "Incorrect": v["incorrect"],
            "Accuracy %": v["accuracy_pct"],
        }
        for k, v in s2.items()
        if k in _s2_labels
    ]
    st.dataframe(
        pd.DataFrame(s2_rows).style.applymap(_colour_pct, subset=["Accuracy %"]),
        use_container_width=True,
        hide_index=True,
    )

    # -----------------------------------------------------------------------
    # Section 3 — Classification Accuracy
    # -----------------------------------------------------------------------
    st.subheader("Section 3 — Classification Accuracy")
    s3 = result["section3"]

    _s3_labels = {
        "is_private_label":         "Is Private Label",
        "is_branded_private_label": "Is Branded Private Label",
        "product_type":             "Product Type",
    }
    s3_rows = [
        {
            "Field": _s3_labels.get(k, k),
            "Correct": v["correct"],
            "Incorrect": v["incorrect"],
            "Accuracy %": v["accuracy_pct"],
        }
        for k, v in s3.items()
        if isinstance(v, dict) and "correct" in v
    ]
    st.dataframe(
        pd.DataFrame(s3_rows).style.applymap(_colour_pct, subset=["Accuracy %"]),
        use_container_width=True,
        hide_index=True,
    )

    flagged_pt = s3.get("product_type", {}).get("flagged", [])
    if flagged_pt:
        with st.expander(f"Flagged product_type rows ({len(flagged_pt)})"):
            st.dataframe(
                pd.DataFrame(flagged_pt),
                use_container_width=True,
                hide_index=True,
            )

    # -----------------------------------------------------------------------
    # Section 4 — Extraction Method Fields
    # -----------------------------------------------------------------------
    st.subheader("Section 4 — Extraction Method Fields")
    s4 = result["section4"]

    _s4_labels = {
        "extraction_method": "Extraction Method",
        "processing_method": "Processing Method",
        "hpp_treatment":     "HPP Treatment",
        "packaging_type":    "Packaging Type",
    }
    s4_rows = [
        {
            "Field": _s4_labels.get(k, k),
            "Correct": v["correct"],
            "Incorrect": v["incorrect"],
            "Accuracy %": v["accuracy_pct"],
        }
        for k, v in s4.items()
        if k in _s4_labels
    ]
    st.dataframe(
        pd.DataFrame(s4_rows).style.applymap(_colour_pct, subset=["Accuracy %"]),
        use_container_width=True,
        hide_index=True,
    )

    # -----------------------------------------------------------------------
    # Section 5 — Semantic Field Quality Score
    # -----------------------------------------------------------------------
    st.subheader("Section 5 — Semantic Field Quality Score")
    s5 = result["section5"]

    sc1, sc2, sc3, sc4 = st.columns(4)
    sc1.metric("Overall Semantic Score", f"{s5['overall_semantic_score_pct']:.1f}%")
    sc2.metric("Product Name", f"{s5['product_name_score_pct']:.1f}%")
    sc3.metric("Flavor", f"{s5['flavor_score_pct']:.1f}%")
    sc4.metric("Brand", f"{s5['brand_score_pct']:.1f}%")

    flagged_semantic = s5.get("flagged_rows", [])
    if flagged_semantic:
        with st.expander(
            f"Rows with severe semantic deviation ({len(flagged_semantic)})"
        ):
            st.dataframe(
                pd.DataFrame(flagged_semantic),
                use_container_width=True,
                hide_index=True,
            )
    else:
        st.success("No severe semantic deviations detected.")

    # -----------------------------------------------------------------------
    # Section 6 — Flagged Rows Table
    # -----------------------------------------------------------------------
    st.subheader("Section 6 — Flagged Rows")
    s6 = result.get("section6", [])

    if s6:
        n_critical = sum(1 for r in s6 if r.get("severity") == "critical")
        n_warning = sum(1 for r in s6 if r.get("severity") == "warning")
        st.caption(
            f"{len(s6)} flagged (field, SKU) pairs — "
            f"{n_critical} critical | {n_warning} warnings"
        )

        s6_df = pd.DataFrame(s6)

        def _colour_severity_row(row):
            if row.get("severity") == "critical":
                return ["background-color: #FFC7CE; color: #9C0006"] * len(row)
            elif row.get("severity") == "warning":
                return ["background-color: #FFEB9C; color: #9C6500"] * len(row)
            return [""] * len(row)

        st.dataframe(
            s6_df.style.apply(_colour_severity_row, axis=1),
            use_container_width=True,
            hide_index=True,
        )
    else:
        st.success("No critical errors or severe deviations detected.")

    # -----------------------------------------------------------------------
    # SECTION 6 (UI) — Narrative Diagnosis
    # -----------------------------------------------------------------------

    st.divider()
    st.header("6. Narrative Diagnosis")
    st.caption(
        "Call 2: Claude reads the scored results above and produces a written diagnostic. "
        "Scoring (Call 1) always uses Opus Extended Thinking. "
        "The narrative uses Sonnet by default — toggle Deep mode for Opus Extended Thinking."
    )

    diag_col1, diag_col2 = st.columns(2)

    with diag_col1:
        if st.button(
            "Quick Narrative (Sonnet)",
            type="secondary",
            use_container_width=True,
            help="Uses claude-sonnet-4-6. Fast and cheap.",
        ):
            with st.spinner("Running narrative with claude-sonnet-4-6..."):
                try:
                    from accuracy_tester.diagnostics import run_narrative_diagnosis
                    text = run_narrative_diagnosis(
                        semantic_result=result,
                        api_key=st.secrets["anthropic_api_key"],
                        deep=False,
                    )
                    st.session_state["at_diagnosis_text"] = text
                    st.session_state["at_diagnosis_mode"] = "Quick (claude-sonnet-4-6)"
                except Exception as e:
                    st.error(f"Narrative diagnosis failed: {e}")

    with diag_col2:
        deep_confirm = st.checkbox(
            "I understand this uses Opus + Extended Thinking (expensive)",
            key="at_deep_confirm",
        )
        if st.button(
            "Deep Narrative (Opus Extended Thinking)",
            type="secondary",
            use_container_width=True,
            disabled=not deep_confirm,
            help="Uses claude-opus-4-6 with Extended Thinking. Thorough but costly.",
        ):
            with st.spinner("Running deep narrative with claude-opus-4-6 Extended Thinking..."):
                try:
                    from accuracy_tester.diagnostics import run_narrative_diagnosis
                    text = run_narrative_diagnosis(
                        semantic_result=result,
                        api_key=st.secrets["anthropic_api_key"],
                        deep=True,
                    )
                    st.session_state["at_diagnosis_text"] = text
                    st.session_state["at_diagnosis_mode"] = "Deep (claude-opus-4-6 Extended Thinking)"
                except Exception as e:
                    st.error(f"Narrative diagnosis failed: {e}")

    if st.session_state.get("at_diagnosis_text"):
        st.subheader(f"Narrative — {st.session_state['at_diagnosis_mode']}")
        st.markdown(st.session_state["at_diagnosis_text"])

        st.download_button(
            label="Download Narrative as .txt",
            data=st.session_state["at_diagnosis_text"],
            file_name="accuracy_narrative.txt",
            mime="text/plain",
        )
