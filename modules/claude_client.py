"""
modules/claude_client.py — Claude API communication.

This module handles sending photos and prompts to Claude Opus 4.6 Extended Thinking
and parsing the JSON response.

Uses streaming to show real-time progress (thinking vs. generating phases).
Images are resized/compressed before sending to minimize upload payload.

Returns both the parsed SKU data and token usage statistics.
"""

import base64
import json
import re
import time
import streamlit as st
from anthropic import Anthropic
from config import CLAUDE_CONFIG
from modules.image_processor import resize_image


def analyze_shelf(
    system_prompt: str,
    user_prompt: str,
    photos: list[dict]
) -> dict:
    """
    Send photos and prompts to Claude API (streaming) and return parsed results + usage.

    Args:
        system_prompt: The system prompt string (from SYSTEM_PROMPT)
        user_prompt: The assembled analysis prompt string (from build_prompt)
        photos: List of dictionaries, each with keys:
                - filename: str (e.g., "foto_1.jpg")
                - type: str ("Overview" or "Close-up")
                - group: int (group number)
                - data: bytes (raw image bytes from Streamlit file uploader)

    Returns:
        Dictionary with keys:
        - skus: List of dictionaries, each representing one SKU row
        - usage: Dict with input_tokens, output_tokens
        - elapsed_seconds: float, total API call time
        - image_savings: Dict with original_bytes, processed_bytes

    Raises:
        Exception: If API call fails or response is invalid JSON
    """
    client = Anthropic(api_key=st.secrets["anthropic_api_key"], timeout=300.0)

    # Build the messages content array
    content = []
    total_original_bytes = 0
    total_processed_bytes = 0

    for idx, photo in enumerate(photos, start=1):
        # Text label for this photo
        photo_label = f"[Photo: {photo['filename']} | {photo['type']} | Group {photo['group']}]"
        content.append({"type": "text", "text": photo_label})

        # Resize and compress the image
        original_bytes = photo["data"]
        processed_bytes, media_type = resize_image(original_bytes, photo["filename"])

        total_original_bytes += len(original_bytes)
        total_processed_bytes += len(processed_bytes)

        # Base64 encode the processed image
        image_base64 = base64.b64encode(processed_bytes).decode("utf-8")

        content.append({
            "type": "image",
            "source": {
                "type": "base64",
                "media_type": media_type,
                "data": image_base64
            }
        })

    # Append user prompt as final text block
    content.append({"type": "text", "text": user_prompt})

    start_time = time.time()
    collected_text = ""

    try:
        with client.messages.stream(
            model=CLAUDE_CONFIG["model"],
            max_tokens=CLAUDE_CONFIG["max_tokens"],
            thinking=CLAUDE_CONFIG["thinking"],
            system=system_prompt,
            messages=[{"role": "user", "content": content}]
        ) as stream:
            for event in stream:
                event_type = getattr(event, "type", None)

                if event_type == "content_block_delta":
                    delta = event.delta
                    if getattr(delta, "type", None) == "text_delta":
                        collected_text += delta.text

            final_message = stream.get_final_message()

        if final_message.stop_reason == "max_tokens":
            raise Exception(
                f"Claude's response was truncated (hit the {CLAUDE_CONFIG['max_tokens']:,} token limit). "
                f"The JSON output is incomplete. Try reducing the number of photos per batch, "
                f"or increase max_tokens in config.py."
            )

        elapsed = time.time() - start_time

        # Extract usage from the final message
        usage = {
            "input_tokens": final_message.usage.input_tokens,
            "output_tokens": final_message.usage.output_tokens,
        }

        response_text = collected_text.strip()

        # Strip markdown code fences if present
        if response_text.startswith("```json"):
            response_text = response_text[7:]
        if response_text.startswith("```"):
            response_text = response_text[3:]
        if response_text.endswith("```"):
            response_text = response_text[:-3]
        response_text = response_text.strip()

        # Try direct parse first
        parsed_json = None
        try:
            parsed_json = json.loads(response_text)
        except json.JSONDecodeError:
            # Fallback: extract the JSON array from surrounding text
            match = re.search(r'\[.*\]', response_text, re.DOTALL)
            if match:
                try:
                    parsed_json = json.loads(match.group(0))
                except json.JSONDecodeError:
                    pass

        if parsed_json is None:
            preview = response_text[:500] if len(response_text) > 500 else response_text
            error_msg = (
                f"Claude returned invalid JSON. Could not parse a JSON array from the response.\n\n"
                f"Raw response preview:\n{preview}"
            )
            raise Exception(error_msg)

        return {
            "skus": parsed_json,
            "usage": usage,
            "elapsed_seconds": elapsed,
            "image_savings": {
                "original_bytes": total_original_bytes,
                "processed_bytes": total_processed_bytes,
            },
            "raw_response": response_text
        }

    except Exception as e:
        # Re-raise the exception to be handled by the caller
        raise
