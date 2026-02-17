"""
modules/claude_client.py — Claude API communication.

This module handles sending photos and prompts to Claude Opus 4.6 Extended Thinking
and parsing the JSON response.

Critical design principle: ONE API call per analysis.
All photos + metadata + transcript are sent together in a single request.
"""

import base64
import json
import streamlit as st
from anthropic import Anthropic
from config import CLAUDE_CONFIG


def analyze_shelf(
    system_prompt: str,
    user_prompt: str,
    photos: list[dict]
) -> list[dict]:
    """
    Send photos and prompts to Claude API and return parsed JSON response.
    
    Args:
        system_prompt: The system prompt string (from SYSTEM_PROMPT)
        user_prompt: The assembled analysis prompt string (from build_prompt)
        photos: List of dictionaries, each with keys:
                - filename: str (e.g., "foto_1.jpg")
                - type: str ("Overview" or "Close-up")
                - group: int (group number)
                - data: bytes (raw image bytes from Streamlit file uploader)
    
    Returns:
        List of dictionaries, each representing one SKU row
    
    Raises:
        Exception: If API call fails or response is invalid JSON
    """
    # Initialize Anthropic client with API key from secrets and extended timeout
    client = Anthropic(api_key=st.secrets["anthropic_api_key"], timeout=300.0)
    
    st.write(f"DEBUG: Client initialized, preparing {len(photos)} photos...")
    
    # Build the messages content array for the user message
    content = []
    
    # Add each photo as TWO content blocks: text label + image
    for idx, photo in enumerate(photos, start=1):
        st.write(f"DEBUG: Encoding photo {idx}/{len(photos)}: {photo['filename']}")
        
        # Block 1: Text label for this photo
        photo_label = f"[Photo: {photo['filename']} | {photo['type']} | Group {photo['group']}]"
        content.append({
            "type": "text",
            "text": photo_label
        })
        
        # Block 2: Image data
        # Detect media type from filename extension
        filename_lower = photo['filename'].lower()
        if filename_lower.endswith('.jpg') or filename_lower.endswith('.jpeg'):
            media_type = "image/jpeg"
        elif filename_lower.endswith('.png'):
            media_type = "image/png"
        else:
            # Default to jpeg if unknown
            media_type = "image/jpeg"
        
        # Encode image bytes as base64 string
        image_base64 = base64.b64encode(photo['data']).decode('utf-8')
        
        content.append({
            "type": "image",
            "source": {
                "type": "base64",
                "media_type": media_type,
                "data": image_base64
            }
        })
    
    # After all photos, add the user prompt as final text block
    content.append({
        "type": "text",
        "text": user_prompt
    })
    
    st.write("DEBUG: All photos encoded, starting API call to Claude...")
    st.write(f"DEBUG: Model={CLAUDE_CONFIG['model']}, max_tokens={CLAUDE_CONFIG['max_tokens']}, thinking_budget={CLAUDE_CONFIG['thinking']['budget_tokens']}")
    st.write("DEBUG: Calling client.messages.create() - this may take 2-5 minutes...")
    
    # Call the Anthropic API
    import time
    start_time = time.time()
    try:
        response = client.messages.create(
            model=CLAUDE_CONFIG["model"],
            max_tokens=CLAUDE_CONFIG["max_tokens"],
            thinking=CLAUDE_CONFIG["thinking"],
            system=system_prompt,
            messages=[
                {
                    "role": "user",
                    "content": content
                }
            ]
        )
        
        elapsed = time.time() - start_time
        st.write(f"DEBUG: API call completed in {elapsed:.1f} seconds, parsing response...")
        st.write(f"DEBUG: Stop reason: {response.stop_reason}")
        st.write(f"DEBUG: Usage - Input: {response.usage.input_tokens}, Output: {response.usage.output_tokens}")
        
        # Parse the response
        # Loop through response.content blocks and collect text blocks
        text_blocks = []
        for block in response.content:
            # Skip thinking blocks
            if block.type == "thinking":
                continue
            # Collect text blocks
            if block.type == "text":
                text_blocks.append(block.text)
        
        # Join all text blocks into one string
        response_text = "".join(text_blocks)
        
        # Strip markdown code fences if present
        response_text = response_text.strip()
        if response_text.startswith("```json"):
            response_text = response_text[7:]  # Remove ```json
        if response_text.startswith("```"):
            response_text = response_text[3:]  # Remove ```
        if response_text.endswith("```"):
            response_text = response_text[:-3]  # Remove trailing ```
        response_text = response_text.strip()
        
        # Parse as JSON
        try:
            st.write("DEBUG: Parsing JSON response...")
            parsed_json = json.loads(response_text)
            st.write(f"DEBUG: JSON parsed successfully, found {len(parsed_json)} SKUs")
            return parsed_json
        except json.JSONDecodeError as e:
            error_msg = f"Claude returned invalid JSON. Parse error: {str(e)}\n\nRaw response text:\n{response_text}"
            st.error(error_msg)
            raise Exception(error_msg)
    
    except Exception as e:
        st.write(f"DEBUG: Exception occurred: {type(e).__name__}")
        # Check if it's an Anthropic API error
        if hasattr(e, '__class__') and 'anthropic' in str(type(e)).lower():
            error_msg = f"Anthropic API error: {str(e)}"
            st.error(error_msg)
            raise Exception(error_msg)
        else:
            # Re-raise other exceptions with full details
            st.error(f"Unexpected error: {str(e)}")
            raise
