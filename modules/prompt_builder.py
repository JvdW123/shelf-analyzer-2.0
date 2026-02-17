"""
modules/prompt_builder.py — Assembles the complete analysis prompt.

This module takes metadata, photo tags, and optional transcript text,
and fills in the placeholders in the ANALYSIS_PROMPT template from
prompts/shelf_analysis.py.
"""

from prompts.shelf_analysis import ANALYSIS_PROMPT
from config import EXCHANGE_RATES


def build_prompt(
    metadata: dict,
    photo_tags: list[dict],
    transcript_text: str | None = None
) -> str:
    """
    Build the complete analysis prompt by filling in template placeholders.
    
    Args:
        metadata: Dictionary with keys: country, city, retailer, store_format,
                  store_name, shelf_location, currency, exchange_rate
        photo_tags: List of dictionaries, each with keys: filename, type, group
                    Example: [{"filename": "foto_1.jpg", "type": "Overview", "group": 1}, ...]
        transcript_text: Optional string containing transcript content, or None
    
    Returns:
        Complete prompt string with all placeholders filled in
    """
    # Build metadata block
    metadata_block = _build_metadata_block(metadata)
    
    # Build photo list block
    photo_list_block = _build_photo_list_block(photo_tags)
    
    # Build transcript block
    transcript_block = _build_transcript_block(transcript_text)
    
    # Fill in the template placeholders
    complete_prompt = ANALYSIS_PROMPT.format(
        metadata_block=metadata_block,
        photo_list_block=photo_list_block,
        transcript_block=transcript_block
    )
    
    return complete_prompt


def _build_metadata_block(metadata: dict) -> str:
    """
    Build the metadata block string from metadata dictionary.
    
    Example output:
    - Country: United Kingdom
    - City: London
    - Retailer: Tesco
    - Store Format: Supermarket
    - Store Name: Tesco London
    - Shelf Location: Chilled Juice Section
    - Currency: GBP
    - Exchange Rate: 1 GBP = 1.17 EUR
    """
    # Get exchange rate from config
    exchange_rate = EXCHANGE_RATES["GBP_TO_EUR"]
    
    lines = [
        f"- Country: {metadata['country']}",
        f"- City: {metadata['city']}",
        f"- Retailer: {metadata['retailer']}",
        f"- Store Format: {metadata['store_format']}",
        f"- Store Name: {metadata['store_name']}",
        f"- Shelf Location: {metadata['shelf_location']}",
        f"- Currency: {metadata['currency']}",
        f"- Exchange Rate: 1 GBP = {exchange_rate} EUR"
    ]
    
    return "\n".join(lines)


def _build_photo_list_block(photo_tags: list[dict]) -> str:
    """
    Build the photo list block string from photo tags list.
    
    Example output:
    [Photo 1: foto_1.jpg | Overview | Group 1]
    [Photo 2: foto_1a.jpg | Close-up | Group 1]
    [Photo 3: foto_2.jpg | Overview | Group 2]
    """
    lines = []
    for i, photo in enumerate(photo_tags, start=1):
        line = f"[Photo {i}: {photo['filename']} | {photo['type']} | Group {photo['group']}]"
        lines.append(line)
    
    return "\n".join(lines)


def _build_transcript_block(transcript_text: str | None) -> str:
    """
    Build the transcript block string.
    
    Returns:
    - If transcript_text is provided: "## TRANSCRIPT\n\n{transcript_text}"
    - If None or empty: "" (empty string)
    """
    if transcript_text and transcript_text.strip():
        return f"## TRANSCRIPT\n\n{transcript_text}"
    else:
        return ""
