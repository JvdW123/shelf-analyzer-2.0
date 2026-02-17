"""
Shelf Analyzer 2.0 — Main Streamlit Application

This file contains the complete UI:
- Password gate (login screen)
- Metadata form (store information)
- Photo upload and tagging
- Transcript upload
"""

import streamlit as st
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
        # Create a 3-column layout for each photo
        col1, col2, col3 = st.columns([1, 2, 2])
        
        with col1:
            # Display thumbnail (column 1)
            st.image(photo, width=150)
        
        with col2:
            # Photo type dropdown (column 2)
            photo_type = st.selectbox(
                "Photo Type",
                options=PHOTO_TYPES,
                key=f"type_{i}",
                label_visibility="visible" if i == 0 else "collapsed"
            )
        
        with col3:
            # Group number input (column 3)
            group_number = st.number_input(
                "Group",
                min_value=1,
                value=1,
                step=1,
                key=f"group_{i}",
                label_visibility="visible" if i == 0 else "collapsed"
            )
        
        # Store this photo's metadata
        photo_tags.append({
            "filename": photo.name,
            "type": photo_type,
            "group": group_number,
            "data": photo.getvalue()  # Store the actual file bytes
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
# SECTION 4 — ANALYZE BUTTON (placeholder)
# ==============================================================================

st.divider()

# Analyze button (disabled for now — will be connected in Phase 3)
st.button("Analyze Shelf", disabled=True, type="primary")
st.info("Analysis will be connected in Phase 3.")

# ==============================================================================
# TEMPORARY DEBUG SECTION — Preview Prompt
# ==============================================================================
# TEMPORARY — remove after Phase 2 testing

if uploaded_photos:
    with st.expander("Debug: Preview Prompt"):
        from modules.prompt_builder import build_prompt
        from config import EXCHANGE_RATES
        
        # Build metadata dictionary from session state
        # Handle "Other" selections by using the custom text input
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
