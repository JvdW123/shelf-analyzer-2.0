"""
modules/gemini_client.py — Gemini API communication.

This module handles sending photos and prompts to Gemini 3 Flash
and parsing the structured JSON response.

Uses responseMimeType "application/json" with a response schema derived
from COLUMN_SCHEMA so Gemini returns valid JSON natively — no parsing
or stripping of markdown fences needed.

Images are sent as raw inline bytes (no resize, no base64 encoding).

Returns the same data structure as claude_client.py so the rest of the
pipeline (excel_generator.py etc.) works unchanged.
"""

import json
import time
import streamlit as st
from google import genai
from google.genai import types
from config import GEMINI_CONFIG, COLUMN_SCHEMA
from modules.image_processor import resize_image

METADATA_KEYS = frozenset([
    "country", "city", "retailer", "store_format",
    "store_name", "shelf_location", "currency",
])

_TYPE_MAP = {
    "text": "STRING",
    "integer": "INTEGER",
    "float": "NUMBER",
}

NULLABLE_KEYS = frozenset([
    "price_local", "price_eur", "price_per_liter_eur",
    "packaging_size_ml", "est_linear_meters",
])


def _build_response_schema() -> dict:
    """Build a Gemini response schema from COLUMN_SCHEMA for the 27 AI-returned keys."""
    properties = {}
    required = []

    for col in COLUMN_SCHEMA:
        key = col["key"]
        if key in METADATA_KEYS:
            continue

        schema_type = _TYPE_MAP.get(col["type"], "STRING")
        prop: dict = {"type": schema_type}
        if key in NULLABLE_KEYS:
            prop["nullable"] = True

        properties[key] = prop
        required.append(key)

    return {
        "type": "ARRAY",
        "items": {
            "type": "OBJECT",
            "properties": properties,
            "required": required,
        },
    }


def analyze_shelf(
    system_prompt: str,
    user_prompt: str,
    photos: list[dict],
) -> dict:
    """
    Send photos and prompts to Gemini API and return parsed results + usage.

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
        - raw_response: str, the raw JSON text from Gemini

    Raises:
        Exception: If API call fails or response cannot be parsed
    """
    client = genai.Client(
        api_key=st.secrets["gemini_api_key"],
        http_options=types.HttpOptions(timeout=120_000),
    )

    contents: list[types.Part] = []
    total_original_bytes = 0
    total_processed_bytes = 0

    for photo in photos:
        photo_label = f"[Photo: {photo['filename']} | {photo['type']} | Group {photo['group']}]"
        contents.append(types.Part.from_text(text=photo_label))

        original_bytes = photo["data"]
        processed_bytes, _ = resize_image(original_bytes, photo["filename"])

        total_original_bytes += len(original_bytes)
        total_processed_bytes += len(processed_bytes)
        contents.append(
            types.Part.from_bytes(data=processed_bytes, mime_type="image/jpeg")
        )

    contents.append(types.Part.from_text(text=user_prompt))

    config = types.GenerateContentConfig(
        system_instruction=system_prompt,
        thinking_config=types.ThinkingConfig(
            thinking_level=GEMINI_CONFIG["thinking_level"],
        ),
        response_mime_type="application/json",
        response_schema=_build_response_schema(),
    )

    start_time = time.time()

    try:
        response = client.models.generate_content(
            model=GEMINI_CONFIG["model"],
            contents=contents,
            config=config,
        )

        elapsed = time.time() - start_time
        response_text = response.text or ""

        try:
            parsed_json = json.loads(response_text)
        except json.JSONDecodeError:
            preview = response_text[:500] if len(response_text) > 500 else response_text
            raise Exception(
                f"Gemini returned invalid JSON despite response schema enforcement.\n\n"
                f"Raw response preview:\n{preview}"
            )

        usage_meta = response.usage_metadata
        usage = {
            "input_tokens": getattr(usage_meta, "prompt_token_count", 0) or 0,
            "output_tokens": getattr(usage_meta, "candidates_token_count", 0) or 0,
        }

        return {
            "skus": parsed_json,
            "usage": usage,
            "elapsed_seconds": elapsed,
            "image_savings": {
                "original_bytes": total_original_bytes,
                "processed_bytes": total_processed_bytes,
            },
            "raw_response": response_text,
        }

    except Exception:
        raise
