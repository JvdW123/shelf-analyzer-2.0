"""
Shelf Analyzer 2.0 — Main Streamlit Application

This file contains the complete UI:
- Password gate (login screen)
- Metadata form (store information)
- Photo upload and tagging
- Transcript upload
"""

import io
import streamlit as st
from PIL import Image
from config import (
    COUNTRIES,
    RETAILERS,
    STORE_FORMATS,
    SHELF_LOCATIONS,
    CURRENCIES,
    PHOTO_TYPES
)

# ==============================================================================
# PAGE CONFIGURATION
# ==============================================================================

st.set_page_config(page_title="Shelf Analyzer 2.0", layout="wide")

# ==============================================================================
# SESSION STATE INITIALIZATION
# ==============================================================================

# Initialize authentication state
if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False

# Initialize metadata fields in session state
if "country" not in st.session_state:
    st.session_state["country"] = COUNTRIES[0]
if "city" not in st.session_state:
    st.session_state["city"] = ""
if "retailer" not in st.session_state:
    st.session_state["retailer"] = None
if "retailer_other" not in st.session_state:
    st.session_state["retailer_other"] = ""
if "store_format" not in st.session_state:
    st.session_state["store_format"] = STORE_FORMATS[0]
if "store_format_other" not in st.session_state:
    st.session_state["store_format_other"] = ""
if "store_name" not in st.session_state:
    st.session_state["store_name"] = ""
if "shelf_location" not in st.session_state:
    st.session_state["shelf_location"] = SHELF_LOCATIONS[0]
if "shelf_location_other" not in st.session_state:
    st.session_state["shelf_location_other"] = ""
if "currency" not in st.session_state:
    st.session_state["currency"] = CURRENCIES[0]

# Initialize photo and transcript storage
if "photo_tags" not in st.session_state:
    st.session_state["photo_tags"] = []
if "transcript_text" not in st.session_state:
    st.session_state["transcript_text"] = None

# ==============================================================================
# PART 1 — PASSWORD GATE
# ==============================================================================

if not st.session_state["authenticated"]:
    # Center the login screen using columns
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.title("Shelf Analyzer 2.0")
        st.write("")  # Add spacing
        
        # Password input field
        password_input = st.text_input(
            "Enter Password",
            type="password",
            key="password_field"
        )
        
        # Login button
        if st.button("Login", type="primary", use_container_width=True):
            # Check password against secrets
            if password_input == st.secrets["app_password"]:
                st.session_state["authenticated"] = True
                st.rerun()
            else:
                st.error("Incorrect password")
    
    # Stop execution here if not authenticated
    st.stop()

# ==============================================================================
# PART 2 — METADATA FORM (shown only after login)
# ==============================================================================

st.title("Shelf Analyzer 2.0")
st.caption("Upload shelf photos, get structured Excel reports.")
st.header("Store Information")

# Row 1: Country and City
col1, col2 = st.columns(2)

with col1:
    country = st.selectbox(
        "Country",
        options=COUNTRIES,
        key="country"
    )

with col2:
    city = st.text_input(
        "City",
        key="city"
    )

# Row 2: Retailer and Store Format
col1, col2 = st.columns(2)

with col1:
    # Dynamic retailer dropdown based on selected country
    if country == "Other":
        retailer_options = ["Other"]
    elif country in RETAILERS:
        retailer_options = RETAILERS[country]
    else:
        retailer_options = ["Other"]
    
    retailer = st.selectbox(
        "Retailer",
        options=retailer_options,
        key="retailer"
    )
    
    # Show free text input if "Other" is selected
    if retailer == "Other":
        retailer_other = st.text_input(
            "Specify Retailer",
            key="retailer_other"
        )

with col2:
    store_format = st.selectbox(
        "Store Format",
        options=STORE_FORMATS,
        key="store_format"
    )
    
    # Show free text input if "Other" is selected
    if store_format == "Other":
        store_format_other = st.text_input(
            "Specify Store Format",
            key="store_format_other"
        )

# Row 3: Store Name and Shelf Location
col1, col2 = st.columns(2)

with col1:
    store_name = st.text_input(
        "Store Name",
        key="store_name"
    )

with col2:
    shelf_location = st.selectbox(
        "Shelf Location",
        options=SHELF_LOCATIONS,
        key="shelf_location"
    )
    
    # Show free text input if "Other" is selected
    if shelf_location == "Other":
        shelf_location_other = st.text_input(
            "Specify Shelf Location",
            key="shelf_location_other"
        )

# Row 4: Currency
currency = st.selectbox(
    "Currency",
    options=CURRENCIES,
    key="currency"
)

# ==============================================================================
# SECTION 1 — PHOTO UPLOAD
# ==============================================================================

st.divider()
st.header("Photos")

# File uploader for multiple photos
uploaded_photos = st.file_uploader(
    "Upload shelf photos",
    type=["jpg", "jpeg", "png"],
    accept_multiple_files=True,
    key="photo_uploader"
)

# ==============================================================================
# SECTION 2 — PHOTO TAGGING
# ==============================================================================

# If photos are uploaded, display each with tagging controls
if uploaded_photos:
    st.write("")  # Add spacing
    
    # Store photo tags in session state
    # Each photo gets: filename, type (Overview/Close-up), group number, and file data
    photo_tags = []
    
    for i, photo in enumerate(uploaded_photos):
        rot_key = f"rotation_{i}"
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
                    if st.button("\u21BA", key=f"rot_ccw_{i}", help="Rotate counter-clockwise"):
                        st.session_state[rot_key] = (st.session_state[rot_key] - 90) % 360
                        st.rerun()
                with r2:
                    if st.button("\u21BB", key=f"rot_cw_{i}", help="Rotate clockwise"):
                        st.session_state[rot_key] = (st.session_state[rot_key] + 90) % 360
                        st.rerun()
            with ctrl_type:
                photo_type = st.selectbox(
                    "Photo Type",
                    options=PHOTO_TYPES,
                    key=f"type_{i}"
                )
            with ctrl_group:
                group_number = st.number_input(
                    "Group",
                    min_value=1,
                    value=1,
                    step=1,
                    key=f"group_{i}"
                )

        st.divider()
        
        rotated_buf = io.BytesIO()
        img.convert("RGB").save(rotated_buf, format="JPEG", quality=95)
        photo_tags.append({
            "filename": photo.name,
            "type": photo_type,
            "group": group_number,
            "data": rotated_buf.getvalue()
        })
    
    # Update session state with all photo tags
    st.session_state["photo_tags"] = photo_tags

# ==============================================================================
# SECTION 3 — TRANSCRIPT UPLOAD
# ==============================================================================

st.divider()
st.header("Transcript (Optional)")

# File uploader for transcript text file
uploaded_transcript = st.file_uploader(
    "Upload voice transcript",
    type=["txt"],
    key="transcript_uploader"
)

# If transcript is uploaded, read and store its content
if uploaded_transcript:
    transcript_text = uploaded_transcript.read().decode("utf-8")
    st.session_state["transcript_text"] = transcript_text
    st.success(f"Transcript loaded: {len(transcript_text)} characters")
else:
    st.session_state["transcript_text"] = None

# ==============================================================================
# SECTION 4 — ANALYZE BUTTON
# ==============================================================================

st.divider()

# Check if all required fields are filled
# Required: at least one photo, country, city, retailer, store name
photos_uploaded = len(st.session_state.get("photo_tags", [])) > 0
city_filled = st.session_state.get("city", "").strip() != ""
store_name_filled = st.session_state.get("store_name", "").strip() != ""

# Handle "Other" retailer case
retailer_value = st.session_state.get("retailer")
if retailer_value == "Other":
    retailer_filled = st.session_state.get("retailer_other", "").strip() != ""
else:
    retailer_filled = retailer_value is not None and retailer_value != ""

# Enable button only if all requirements are met
can_analyze = photos_uploaded and city_filled and retailer_filled and store_name_filled


def validate_metadata() -> tuple[bool, list[str]]:
    """
    Validate all required metadata fields before API call.
    
    Returns:
        Tuple of (is_valid, list_of_missing_fields)
    """
    missing_fields = []
    
    # Check country (should always be filled from dropdown)
    if not st.session_state.get("country", "").strip():
        missing_fields.append("Country")
    
    # Check city
    if not st.session_state.get("city", "").strip():
        missing_fields.append("City")
    
    # Check retailer
    retailer = st.session_state.get("retailer")
    if not retailer:
        missing_fields.append("Retailer")
    elif retailer == "Other" and not st.session_state.get("retailer_other", "").strip():
        missing_fields.append("Retailer (specify)")
    
    # Check store format (if "Other" selected)
    store_format = st.session_state.get("store_format")
    if store_format == "Other" and not st.session_state.get("store_format_other", "").strip():
        missing_fields.append("Store Format (specify)")
    
    # Check store name
    if not st.session_state.get("store_name", "").strip():
        missing_fields.append("Store Name")
    
    # Check shelf location (if "Other" selected)
    shelf_location = st.session_state.get("shelf_location")
    if shelf_location == "Other" and not st.session_state.get("shelf_location_other", "").strip():
        missing_fields.append("Shelf Location (specify)")
    
    return len(missing_fields) == 0, missing_fields


# Analyze button
if st.button("Analyze Shelf", disabled=not can_analyze, type="primary"):
    # Validate metadata before proceeding
    is_valid, missing_fields = validate_metadata()
    
    if not is_valid:
        st.warning(f"Please fill in the following required fields: {', '.join(missing_fields)}")
    else:
        # Import required modules
        from modules.prompt_builder import build_prompt
        from modules.claude_client import analyze_shelf
        from prompts.shelf_analysis import SYSTEM_PROMPT
        from config import EXCHANGE_RATES, PRICING
        import anthropic
        import json
        
        # Show progress status with detailed steps
        with st.status("Analyzing shelf photos...", expanded=True) as status:
            try:
                # Step 1: Prepare photos
                num_photos = len(st.session_state['photo_tags'])
                st.write(f"Step 1: Preparing {num_photos} photos for analysis...")
                
                # Build metadata dictionary
                final_retailer = (
                    st.session_state["retailer_other"] 
                    if st.session_state["retailer"] == "Other" 
                    else st.session_state["retailer"]
                )
                final_store_format = (
                    st.session_state["store_format_other"] 
                    if st.session_state["store_format"] == "Other" 
                    else st.session_state["store_format"]
                )
                final_shelf_location = (
                    st.session_state["shelf_location_other"] 
                    if st.session_state["shelf_location"] == "Other" 
                    else st.session_state["shelf_location"]
                )
                
                metadata = {
                    "country": st.session_state["country"],
                    "city": st.session_state["city"],
                    "retailer": final_retailer,
                    "store_format": final_store_format,
                    "store_name": st.session_state["store_name"],
                    "shelf_location": final_shelf_location,
                    "currency": st.session_state["currency"],
                    "exchange_rate": EXCHANGE_RATES["GBP_TO_EUR"]
                }
                
                # Get photo tags (without 'data' for prompt building)
                photo_tags_for_prompt = [
                    {
                        "filename": tag["filename"],
                        "type": tag["type"],
                        "group": tag["group"]
                    }
                    for tag in st.session_state["photo_tags"]
                ]
                
                # Build the complete prompt
                user_prompt = build_prompt(
                    metadata=metadata,
                    photo_tags=photo_tags_for_prompt,
                    transcript_text=st.session_state["transcript_text"]
                )
                
                # Store prompt for debug view
                st.session_state["last_prompt"] = user_prompt
                
                # Step 2: Send to Claude
                st.write("Step 2: Sending to Claude Extended Thinking... (this may take 1-3 minutes)")
                
                # Call Claude API (streaming)
                result = analyze_shelf(
                    system_prompt=SYSTEM_PROMPT,
                    user_prompt=user_prompt,
                    photos=st.session_state["photo_tags"]
                )
                
                # Step 3: Parse response
                st.write("Step 3: Parsing response...")
                
                skus = result["skus"]
                
                # Check if result is empty
                if not skus or len(skus) == 0:
                    status.update(label="No SKUs found", state="error", expanded=False)
                    st.error("No SKUs found. Check your photos and try again.")
                else:
                    # Step 4: Complete
                    st.write(f"Step 4: Complete! Found {len(skus)} SKUs.")
                    
                    # Store results
                    st.session_state["analysis_result"] = skus
                    st.session_state["analysis_usage"] = result["usage"]
                    st.session_state["analysis_elapsed"] = result["elapsed_seconds"]
                    st.session_state["analysis_image_savings"] = result["image_savings"]
                    st.session_state["raw_response"] = result.get("raw_response", "")
                    
                    # Update status to complete
                    status.update(label=f"Analysis complete! Found {len(skus)} SKUs.", state="complete", expanded=False)
            
            except anthropic.AuthenticationError:
                status.update(label="Authentication failed", state="error", expanded=False)
                st.error("Invalid API key. Check your settings.")
            
            except anthropic.APITimeoutError:
                status.update(label="Request timed out", state="error", expanded=False)
                st.error("Analysis timed out. Try with fewer photos or try again.")
            
            except anthropic.APIConnectionError:
                status.update(label="Connection failed", state="error", expanded=False)
                st.error("Network error. Check your internet connection.")
            
            except json.JSONDecodeError as e:
                status.update(label="Invalid JSON response", state="error", expanded=False)
                st.error("Claude returned invalid JSON. See details below.")
                raw_response = st.session_state.get("raw_response", "No response captured")
                with st.expander("Raw Response", expanded=True):
                    st.code(raw_response, language="text")
                st.error(f"JSON Parse Error: {str(e)}")
            
            except Exception as e:
                status.update(label="Analysis failed", state="error", expanded=False)
                error_type = type(e).__name__
                st.error(f"Unexpected error ({error_type}): {str(e)}")
                
                # Show traceback in expander for debugging
                import traceback
                with st.expander("Error Details", expanded=False):
                    st.code(traceback.format_exc(), language="text")

# Show results if available
if "analysis_result" in st.session_state and st.session_state["analysis_result"]:
    st.divider()
    st.subheader("Analysis Results")
    
    # Calculate summary statistics
    skus = st.session_state['analysis_result']
    num_skus = len(skus)
    unique_brands = len(set(sku.get("brand", "").strip() for sku in skus if sku.get("brand", "").strip()))
    
    st.write(f"**Found {num_skus} SKUs across {unique_brands} unique brands**")
    
    # Show usage metrics if available
    if "analysis_usage" in st.session_state:
        from config import PRICING
        
        usage = st.session_state["analysis_usage"]
        elapsed = st.session_state.get("analysis_elapsed", 0)
        savings = st.session_state.get("analysis_image_savings", {})
        
        input_tok = usage["input_tokens"]
        output_tok = usage["output_tokens"]
        total_tok = input_tok + output_tok
        
        input_cost = input_tok * PRICING["input_per_million"] / 1_000_000
        output_cost = output_tok * PRICING["output_per_million"] / 1_000_000
        total_cost = input_cost + output_cost
        
        col_m1, col_m2, col_m3, col_m4 = st.columns(4)
        col_m1.metric("Total Tokens", f"{total_tok:,}")
        col_m2.metric("Input Tokens", f"{input_tok:,}")
        col_m3.metric("Output Tokens", f"{output_tok:,}")
        col_m4.metric("Estimated Cost", f"${total_cost:.2f}")
        
        col_t1, col_t2 = st.columns(2)
        col_t1.metric("Processing Time", f"{elapsed:.1f}s")
        if savings.get("original_bytes", 0) > 0:
            orig_mb = savings["original_bytes"] / (1024 * 1024)
            proc_mb = savings["processed_bytes"] / (1024 * 1024)
            col_t2.metric("Image Payload", f"{proc_mb:.1f} MB", delta=f"-{orig_mb - proc_mb:.1f} MB")
    
    # Show a preview of the first few SKUs
    with st.expander("Preview first 3 SKUs"):
        import json
        preview_data = st.session_state['analysis_result'][:3]
        st.json(preview_data)
    
    # ==============================================================================
    # DOWNLOAD EXCEL BUTTON
    # ==============================================================================
    
    from modules.excel_generator import generate_excel
    from datetime import datetime
    
    # Build metadata dictionary for Excel generation
    final_retailer = (
        st.session_state["retailer_other"] 
        if st.session_state["retailer"] == "Other" 
        else st.session_state["retailer"]
    )
    final_store_format = (
        st.session_state["store_format_other"] 
        if st.session_state["store_format"] == "Other" 
        else st.session_state["store_format"]
    )
    final_shelf_location = (
        st.session_state["shelf_location_other"] 
        if st.session_state["shelf_location"] == "Other" 
        else st.session_state["shelf_location"]
    )
    
    metadata_dict = {
        "country": st.session_state["country"],
        "city": st.session_state["city"],
        "retailer": final_retailer,
        "store_format": final_store_format,
        "store_name": st.session_state["store_name"],
        "shelf_location": final_shelf_location,
        "currency": st.session_state["currency"]
    }
    
    # Generate Excel file
    excel_bytes = generate_excel(st.session_state["analysis_result"], metadata_dict)
    
    # Build filename: {Retailer}_{City}_{YYYY-MM-DD}.xlsx
    # Replace spaces with underscores in retailer and city
    retailer_clean = final_retailer.replace(" ", "_")
    city_clean = st.session_state["city"].replace(" ", "_")
    today_date = datetime.now().strftime("%Y-%m-%d")
    filename = f"{retailer_clean}_{city_clean}_{today_date}.xlsx"
    
    # Show download button
    st.download_button(
        label="Download Excel",
        data=excel_bytes,
        file_name=filename,
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        type="primary"
    )

# ==============================================================================
# DEBUG SECTION — Optional Debug Info
# ==============================================================================

if uploaded_photos or "analysis_result" in st.session_state:
    show_debug = st.checkbox("Show debug info", value=False)
    
    if show_debug:
        # Prompt Preview
        if uploaded_photos:
            with st.expander("Prompt Preview", expanded=True):
                from modules.prompt_builder import build_prompt
                from config import EXCHANGE_RATES
                
                # Build metadata dictionary from session state
                final_retailer = (
                    st.session_state["retailer_other"] 
                    if st.session_state["retailer"] == "Other" 
                    else st.session_state["retailer"]
                )
                final_store_format = (
                    st.session_state["store_format_other"] 
                    if st.session_state["store_format"] == "Other" 
                    else st.session_state["store_format"]
                )
                final_shelf_location = (
                    st.session_state["shelf_location_other"] 
                    if st.session_state["shelf_location"] == "Other" 
                    else st.session_state["shelf_location"]
                )
                
                metadata = {
                    "country": st.session_state["country"],
                    "city": st.session_state["city"],
                    "retailer": final_retailer,
                    "store_format": final_store_format,
                    "store_name": st.session_state["store_name"],
                    "shelf_location": final_shelf_location,
                    "currency": st.session_state["currency"],
                    "exchange_rate": EXCHANGE_RATES["GBP_TO_EUR"]
                }
                
                # Get photo tags from session state (without the 'data' field for preview)
                photo_tags_preview = [
                    {
                        "filename": tag["filename"],
                        "type": tag["type"],
                        "group": tag["group"]
                    }
                    for tag in st.session_state["photo_tags"]
                ]
                
                # Build the complete prompt
                complete_prompt = build_prompt(
                    metadata=metadata,
                    photo_tags=photo_tags_preview,
                    transcript_text=st.session_state["transcript_text"]
                )
                
                # Display the prompt in a code block for readability
                st.code(complete_prompt, language="text")
        
        # Raw JSON Response
        if "raw_response" in st.session_state and st.session_state["raw_response"]:
            with st.expander("Raw JSON Response", expanded=True):
                st.code(st.session_state["raw_response"], language="json")
