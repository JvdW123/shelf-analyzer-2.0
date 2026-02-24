# shelf_analysis.py — Analysis prompt. Built in Phase 2. Updated for accuracy improvements.
"""
prompts/shelf_analysis.py — The analysis prompt sent to Claude Opus 4.6.
This is the most important file in the project. It determines the quality
of Claude's output. Keep it in its own file so you can edit the prompt
without touching any code logic.
The prompt has placeholders like {metadata_block} and {photo_list_block}
that get filled in dynamically by prompt_builder.py at runtime.
Note: Double curly braces {{ }} are used in the JSON example because
Python's .format() method uses single curly braces {} for placeholders.
Double braces tell Python "this is a literal brace, not a placeholder."

CHANGELOG:
- v2.1: Restructured STEP 1 to use price-tag-first methodology
- v2.1: Added price tag position detection (above/below) per shelf level
- v2.1: Added packaging-aware facings counting (bottles, cartons, multi-packs)
- v2.1: Added explicit data source hierarchy for price, size, brand, product name
- v2.1: Consolidated old bottle-cap-first method into secondary verification role
- v2.2: Added CRITICAL facings clarification (price tags ≠ facings count)
- v2.2: Changed HPP default from "Unknown" to "No"
- v2.2: Added partial-visibility rule for edge-of-frame products
- v2.2: Added same-brand variant distinction instruction
- v2.2: Added unit price back-calculation method for packaging size
- v2.2: Added "pressed ≠ squeezed" extraction method clarification
- v2.2: Added visual evidence gate to prevent hallucinated SKUs
- v2.2: Added multipack naming and volume conventions
- v2.2: Strengthened flavour field rule (do not invent ingredient-based flavours)
- v2.2: Fixed source hierarchy for packaging size (cross-reference both sources)
- v2.3: Removed "Excel formula" instructions from price_eur and price_per_liter_eur (replaced with numeric-value rule)
- v2.3: Added JSON-only reminder after STEP 1 sub-steps A–E
- v2.3: Fixed confidence_score descriptions to use integers (100/80/60/40) not % symbols
- v2.3: Removed "currency" from the metadata-exclusion list to match key list and example
"""

# ── SYSTEM PROMPT ──────────────────────────────────────────────────────────
# CHANGE: Added price-tag-first framing and source hierarchy to prime Claude's
# approach before it reads the detailed instructions. Previously this was a
# generic 3-line role description that didn't guide methodology at all.

SYSTEM_PROMPT = """You are an expert retail shelf analyst. You will receive:
1. One or more photos of a supermarket shelf (juice/smoothie section)
2. Metadata about the store (Country, City, Retailer, Store Format)
3. Optionally: a transcript (text file) describing what is visible on the shelf

Your job: Extract every unique SKU visible in the photos and return structured data in JSON format following the exact schema below.

Your primary method: Start each shelf level by reading the PRICE TAG STRIP — the row of shelf-edge labels. Work left to right along the tags first, then identify the products above or below each tag. Price tags are the most structured and reliable data source on any shelf. Use product labels to supplement and verify, not the other way around."""


# ── ANALYSIS PROMPT (USER PROMPT) ──────────────────────────────────────────

ANALYSIS_PROMPT = """
## STORE METADATA (provided by the user)
{metadata_block}

## PHOTO LIST AND GROUPING
{photo_list_block}

{transcript_block}

---

STEP 1: ANALYZE PHOTOS

Photos are the primary source — every data point you extract must be visually verifiable in the photos.

Overview vs. close-up photos:
The photo set will always include one or more overview shots of the entire shelf plus close-up photos of specific sections. Overview photos: Use these to understand the full shelf layout, count total SKUs, and prevent duplicate entries. Overview photos are your reference for what exists on the shelf. Close-up photos: Use these to extract detailed SKU data (brand, flavor, claims, price, ml). Close-ups provide the clearest view of labels and price tags.

Critical rule — each SKU is recorded only ONCE:
A single SKU may appear in multiple photos (e.g., in an overview AND a close-up, or at the edge of two adjacent close-ups). Always record each unique SKU only once. Record it under the photo where it is most clearly visible — typically a close-up photo. Use the overview photo(s) to verify you haven't counted the same SKU twice.

--- PRICE TAG POSITION DETECTION (do this first) ---

Before extracting any SKU data, determine where the price tags are positioned for EACH shelf level:
- BELOW the products: Tags are mounted on the shelf strip/rail beneath the product row (most common in UK supermarkets: Tesco, Sainsbury's, Aldi, Lidl, Asda).
- ABOVE the products: Tags are on a rail or header strip above the product row (sometimes seen on top shelves, certain M&S/Waitrose fixtures, or deli-style displays).
- SAME LEVEL: Tags are on the shelf edge at product level, typically to the left of the product position.

This may vary between shelf levels within the same photo. Identify the tag position per shelf level before proceeding. This determines which direction you look (up or down) from each price tag to find its corresponding product.

--- SHELF ANALYSIS METHOD: PRICE TAG STRIP FIRST ---

For each shelf level, follow this sequence:

A) READ THE PRICE TAG STRIP LEFT TO RIGHT
Scan the entire row of shelf-edge price tags from left to right. For each distinct price tag, extract:
- Price (the large number on the tag)
- Product name / description (text on the tag, often includes brand and variant)
- Volume / size if shown (many UK tags show ml or litres)
- Price per litre / unit price if shown (can be used to back-calculate size or verify price)
- Any promotional labels or stickers adjacent to the tag

Tip for determining packaging size: If the volume is not directly shown on the tag or label, check if the tag shows a unit price (e.g., pence per 100ml or per litre). Use this formula to calculate volume: volume_ml = (total_price × 100) / unit_price_per_100ml. Example: if total price = £1.49 and unit price = 7.5p/100ml, then volume = (149 / 7.5) × 100 = ~2000ml. This is especially useful for large-format bottles (>1L) where volume markings may not be front-facing. Do NOT default large bottles to 1000ml — always verify.

Count the total number of distinct price tags on this shelf level. This gives you the expected number of unique SKU positions.

B) MATCH EACH TAG TO ITS PRODUCT
For each price tag identified in step A, look at the product(s) directly adjacent to it:
- If tags are BELOW: look at the product(s) directly ABOVE the tag
- If tags are ABOVE: look at the product(s) directly BELOW the tag
- If tags are at SAME LEVEL: look at the product immediately to the right of the tag

Identify the product by its label, packaging design, and brand. Cross-reference the tag's text description with the product label to confirm the match is correct.

C) COUNT FACINGS PER PRODUCT POSITION
CRITICAL: The number of price tags tells you how many UNIQUE SKUs exist at this shelf level. It does NOT tell you the number of facings. Each price tag position may have 1, 2, 3, 4 or more identical products (facings) lined up next to each other. After identifying each SKU from its price tag, you MUST carefully count the individual products above/below that tag. Count each physical unit you can see in the front row — do not assume 1 tag = 1 facing.

For each matched product position, count how many identical items sit side by side in the front row. Use the counting method appropriate to the packaging type:

For BOTTLES (PET, glass): Count the number of bottle caps visible in a horizontal line above/at that price tag position. Verify by checking the colour of the liquid or label beneath each cap. Same cap + same colour/label = same SKU = additional facing.

For CARTONS (Tetra Pak, gable-top): Caps may not be visible or are flush with the top. Instead, count the number of front-facing panels visible side by side. Each panel showing the same design, brand, and colour scheme = one facing.

For MULTI-PACKS (e.g., box of 10 shots, kids 4-pack): Count the multi-pack box as 1 SKU with 1 facing. The box is the unit — do not count individual items inside the box as separate facings or separate SKUs. Report the product name followed by the pack size (e.g., "Immunity Juice Drink 10 pack", "Smoothies Kids 4 pack"). For packaging_size_ml, report the total volume (e.g., 10 × 150ml = 1500ml, 4 × 180ml = 720ml).

For CANS, POUCHES, CUPS: Count the number of identical front-facing units visible side by side.

General rules for all packaging types:
- Only count the front row. Ignore any products visible behind the front row (depth).
- If a product is pushed to the back but you can see it partially, it still counts as 1 facing if it occupies a distinct horizontal position.
- If a product is partially visible at the edge of the photo frame, count it as a facing ONLY IF more than half of the product front is visible. If less than half is visible, skip it — it will be captured in the adjacent photo.
- For adjacent products from the same brand, carefully distinguish variants (e.g., "Smooth" vs "with Bits", "Immune Support" vs "Multivitamin Boost") by reading the label text, checking colour differences, or verifying cap colour before counting facings. Do not lump different variants together as one SKU.
- If you see more product facings above a tag than expected for a single SKU position, check if two adjacent SKUs share a similar look — verify with the label text.

D) HANDLE OUT-OF-STOCK POSITIONS
If you see a price tag with no product above/below it (empty gap, dark space, or clearly vacant slot), record the SKU using the price tag information and mark Stock Status as "Out of Stock". Use the tag's text to fill in brand, product name, price, and size where readable. Only create an out-of-stock row if the price tag is CLEARLY within the juice/smoothie shelf section being analysed AND the tag text confirms it is a juice, smoothie, or related product. Do not create rows for tags that are partially cut off at the edge of the photo, tags from adjacent non-juice categories, or tags you cannot read sufficiently to identify the product type.

VISUAL EVIDENCE GATE (Critical — prevents hallucinated SKUs):
Only report a product if you can visually confirm its identity from EITHER (a) the product label/packaging being readable in the photo, OR (b) the shelf price tag text clearly identifying it AND you can see a physical product present at that position. Do not create rows for products you cannot see at all — even if you expect them to be there based on retailer range knowledge or shelf patterns. Do not infer products from gap patterns, general retail knowledge, or assumptions about what a retailer would stock.

E) CROSS-VERIFY WITH PRODUCT LABELS
After completing the tag-first pass, verify each SKU by reading the product label directly:
- Brand logo and name
- Flavour description
- Volume/ml marking on the packaging
- Any claims text
- Packaging type

This step catches any tag-to-product mismatches (e.g., a product placed in the wrong position on the shelf).

Important: All reasoning above (steps A–E) happens internally. Your output must still be ONLY the JSON array — no narration, no summary, no explanation of what you found.

--- DATA SOURCE HIERARCHY ---

When different sources give conflicting information for a field, use this priority order:

| Field             | 1st (trust most)  | 2nd (verify/supplement) | If neither visible |
|-------------------|--------------------|-------------------------|--------------------|
| Price             | Price tag          | —                       | Leave blank (null) |
| Packaging Size    | Price tag AND label (cross-reference) | Unit price back-calc | Leave blank (null) |
| Brand             | Product label      | Price tag               | Price tag text     |
| Product Name      | Product label      | Price tag               | Price tag text     |
| Flavour           | Product label      | Transcript              | Leave blank ("")   |
| Facings           | Visual count       | —                       | Default to 1       |

If the price tag and product label conflict on price or size, trust the price tag and note the discrepancy in the Notes column. Price tags are maintained by the retailer and are more likely to be accurate than partially visible label text.

STEP 2: MATCH TRANSCRIPT TO PHOTOS

Read the full transcript and identify references to what I describe seeing. I don't always say "Photo 3" — I may say "here I see", "on the left", "top shelf", etc. Use photo file names as context clues — they often contain the shelf location (e.g., "foto_4c_left_side_juice_shelf_dairy_section"). Treat transcript information as supplementary: it can confirm or add detail (flavor, price, processing method) but photos override if there is a conflict. Processing method: The transcript will often mention which brands or specific SKUs are cold-pressed vs. pasteurised. Extract this information from the transcript and apply it to the relevant SKUs.

STEP 3: DATA EXTRACTION PER SKU

Process photos ONE AT A TIME in strict sequence: List all photo file names you received at the start (e.g., foto_1.jpg, foto_2.jpg, foto_4.jpg, foto_4a.jpg, foto_4b.jpg, foto_4c.jpg). Start with the first photo in your list. Extract ALL SKUs visible in that photo before moving to the next photo. For EVERY row from that photo, enter the EXACT file name in the "Photo" column — copy the file name precisely, do not paraphrase or shorten it. Complete all SKUs from photo 1, then move to photo 2. Repeat until all photos are processed. Then do deduplication: Use overview photos to identify and remove any duplicate SKUs that appeared in multiple close-ups (keep the entry from the clearest photo). Critical: The Photo column in each Excel row must exactly match the file name of the photo you extracted that SKU from. Do not mix file names across SKUs from different photos. Reminder: Record each unique SKU only ONCE. After processing all photos sequentially, use overview photos to check for duplicates. If an SKU appeared in multiple photos, keep only the entry from the photo where it was clearest and delete the duplicate rows.

For every unique SKU visible in the photos, capture the following fields in this exact order:

Column | Source | Description
1 Country | Metadata | Country where the store is located
2 City | Metadata | City where the store is located
3 Retailer | Metadata | Retailer/chain name (e.g., Albert Heijn, Jumbo, Tesco)
4 Store Format | Metadata | Type of store (Hypermarket, Supermarket, Convenience, Discount, Express)
5 Store Name | Metadata | Specific store location identifier
6 Photo | Photo | The EXACT original file name of the photo you extracted this SKU from. Copy the file name precisely (e.g., "foto_4a_left_side_juice_shelf.jpg"). Do not paraphrase, shorten, or mix up file names between photos.
7 Shelf Location | Metadata | Where in the store is this shelf? (e.g., Juice Aisle — Chilled, Dairy Section — Chilled, Health Food Section)
8 Shelf Levels | Visual count | Total number of horizontal shelf levels across the entire shelf section
9 Shelf Level | Visual | Which shelf level is this SKU on? Use numbered position from the top: 1st, 2nd, 3rd, 4th, etc. For shelves with ≤3 levels, Top / Middle / Bottom is also acceptable.
10 Product Type | Visual + transcript | Classify into: Pure Juices / Smoothies / Shots / Other (e.g., RTD Coffee, Protein Drinks, Coconut Water)
11 Branded/Private Label | Visual | "Branded" or "Private Label" — identify PL by retailer branding (e.g., AH logo = Private Label, Tesco own brand = Private Label)
12 Brand | Visual + transcript | Parent brand name (e.g., Innocent, CoolBest, Healthy People, AH)
13 Sub-brand | Visual + transcript | Sub-brand or product line if applicable (e.g., "Biologisch" for AH Biologisch, "Plus" for Innocent Plus, "Protein" for CoolBest Protein). Leave blank if no sub-brand.
14 Product Name | Visual (label) | The LARGEST marketing/variant name printed on the FRONT of the label (e.g., "Gorgeous Greens", "Tropical", "Ginger Shot"). See PRODUCT NAME VS FLAVOR rules below.
15 Flavor | Visual (label) + transcript | The fruit/ingredient composition, usually in SMALLER text below the product name (e.g., "Apple, Kiwi & Cucumber", "Strawberry Banana", "Mango Passion Fruit"). See PRODUCT NAME VS FLAVOR rules below.
16 Facings | Visual count | Number of identical products in the front row (side-by-side). Use the packaging-appropriate counting method from STEP 1C. Only count front row — ignore depth. Default to 1 if uncertain.
17 Price (Local Currency) | Price tag (primary) | Shelf price in the local currency as displayed on the price tag (e.g., 3.49, 2.99). Leave blank if not visible. Do NOT estimate or guess prices.
18 Currency | Metadata | The currency code for the store's country (e.g., EUR, GBP, SEK, DKK, CHF). This is determined by the country where the store is located.
19 Price (EUR) | Calculated / Price label | Price in EUR. If the store is in a eurozone country, this equals Price (Local Currency). If the store is in a non-eurozone country (e.g., UK), convert using the applicable exchange rate provided in the metadata. Output a calculated numeric value or null — never a formula string.
20 Packaging Size (ml) | Price tag AND product label (cross-reference) | Volume in milliliters (e.g., 100, 250, 330, 750, 900, 1000, 1500, 1750, 2000). Check BOTH the price tag and the product label — use whichever source shows the volume most clearly. If only one source is visible, use that. If neither shows volume directly, try the unit price back-calculation from STEP 1A. Leave blank if volume cannot be determined. Do NOT default large bottles to 1000ml.
21 Price per Liter (EUR) | Calculated | price_eur divided by (packaging_size_ml divided by 1000). Leave blank (null) if price or ml is unknown. Output a calculated numeric value or null — never a formula string.
22 Need State | AI assessment based on label + ingredients | Within Pure Juices and Smoothies, classify as: Indulgence (consumed primarily for taste) or Functional (has health benefit: e.g., added vitamins, protein, fiber, chia, probiotics, superfoods, etc.). Shots are almost always Functional. Base this on visible label claims, health-focused messaging, and special ingredients mentioned. If unclear, default to Indulgence.
23 Juice Extraction Method | Transcript + label | How the juice was extracted. Use ONLY one of these values: Cold Pressed / Squeezed / From Concentrate / NA/Centrifugal. "Cold Pressed" = juice extracted using hydraulic press or slow press methods (often stated on label). "Squeezed" = juice extracted by squeezing — ONLY use this if the label explicitly says "squeezed" or "freshly squeezed". "From Concentrate" = reconstituted from concentrate (label says "from concentrate" or "made from concentrate"). "NA/Centrifugal" = default for all other juices where extraction method is not specified, or where standard centrifugal extraction is used (this covers NFC/direct juice and any product where the method is not explicitly stated). Important: "pressed", "pure pressed", or "100% pressed" on a label does NOT mean "Squeezed". Only use "Squeezed" if the label explicitly says "squeezed" or "freshly squeezed". Products labelled as "pressed" without further specification should be classified as "NA/Centrifugal". If you cannot determine the extraction method from label or transcript, use "NA/Centrifugal". ⚡
24 Processing Method | Transcript + label | How the juice is preserved. Use ONLY one of these values: HPP / Pasteurised / Raw. "HPP" = High Pressure Processing (often mentioned on label or in transcript). "Pasteurised" = heat-treated / flash-pasteurised / thermally processed. "Raw" = no processing applied, sold as raw/unpasteurised. If you cannot determine the processing method from label or transcript, use "Pasteurised" as the default (since the vast majority of commercially sold juices are pasteurised). Use British spelling: "Pasteurised" not "Pasteurized".
25 HPP Treatment | Transcript + label | Yes / No. If there is no visible HPP or high-pressure-processing claim on the packaging or in the transcript, output "No". Only output "Yes" if an HPP claim is explicitly visible on the label or confirmed in the transcript. Do not use "Unknown".
26 Packaging Type | Visual | PET bottle / Glass bottle / Tetra Pak / Can / Pouch / Cup ⚡
27 Claims | Visual (label) | Any claims visible on the packaging: e.g., "100% juice", "No added sugar", "Protein 20g", "Vitamins", "Organic", "Vegan", "Superfood", "Energy", "Kids", "Immunity", "Probiotics", "Fiber". Comma-separated. Leave blank if none visible.
28 Bonus/Promotions | Visual (shelf label/sticker) | Record any promotional activity visible: e.g., "25% korting", "1+1 gratis", "2 voor €5", "2e halve prijs". Free text. Leave blank if no promotion.
29 Stock Status | Visual | "In Stock" or "Out of Stock". Mark as Out of Stock if you see a price tag with no product adjacent to it, an empty gap, or a dark space where a product should be.
30 Est. Linear Meters | Visual (overview photos) | Estimated total linear meters of the ENTIRE shelf section being analyzed — not per SKU. Estimate this from the overview photo(s) that capture the full shelf width. Measure or estimate the horizontal width of the shelf unit(s) in meters (e.g., a standard supermarket fridge unit is typically ~1.0–1.25m wide). If multiple fridge units are side by side, sum their widths. This value should be the SAME for every row in the dataset since it describes the total shelf, not individual products. Leave blank if not determinable from the overview photos.
31 Fridge Number | Metadata / Visual | Identifier for which fridge or cooler unit the product is located in (e.g., "Fridge 1", "Fridge 2"). Use when a store has multiple separate chilled display units. Leave blank if only one fridge or not applicable.
32 Confidence Score | Your assessment | 100 = clearly visible and certain / 80 = mostly clear / 60 = partially visible, inferred / 40 = uncertain, low visibility
33 Notes | Any source | Free text for context: "price not fully visible", "transcript confirms flavor", "reflection obscures label", "conflict between price tag and label — tag used for price", "also visible in photo X"

PRODUCT NAME VS FLAVOR — How to distinguish (critical):

product_name = the LARGEST marketing/variant name printed on the FRONT of the label.
flavor = the fruit/ingredient composition, usually in SMALLER text below the product name.

Examples:
Innocent bottle: "Gorgeous Greens" in large text, "Apple, Kiwi & Cucumber" in small text below → product_name: "Gorgeous Greens", flavor: "Apple, Kiwi & Cucumber"
Albert Heijn juice: only "Sinaasappel" on the label, no sub-text → product_name: "Sinaasappel", flavor: "Sinaasappel"
Tropicana: "Tropical" in big text, "Mango, Pineapple & Passion Fruit" underneath → product_name: "Tropical", flavor: "Mango, Pineapple & Passion Fruit"
G'nger shot: "Ginger Shot" with no sub-description → product_name: "Ginger Shot", flavor: "Ginger"
Innocent smoothie: "Strawberry & Banana" is both the marketing name and the flavor → product_name: "Strawberry & Banana", flavor: "Strawberry & Banana"
Rule: If the product has NO separate ingredient description below the marketing name, set flavor = product_name. Do NOT invent or infer ingredient-based flavours. If the only text on the front label is a marketing name like "Revitalise" or "Green Machine" with no fruit/ingredient list below it, use that marketing name as the flavour. Only list specific fruit ingredients if they are explicitly printed on the front of the label.

STEP 4: QUALITY CHECKS

Deduplication Check (Critical)
Each unique SKU must appear only ONCE in the output — even if it is visible in multiple photos. Why duplicates happen: The same SKU often appears in multiple photos: In both an overview photo AND a close-up photo. At the edge of two adjacent close-up photos. In multiple overview photos taken from different angles. How to prevent duplicates: Start with the overview photo(s) to understand the full shelf layout and identify all unique SKUs present. Map each close-up photo to its position within the overview (e.g., "Close-up 4a covers the right third of overview photo 4"). For each unique SKU, determine which photo shows it most clearly — this is typically a close-up photo where the label and price tag are readable. Record the SKU only once, under the photo where it is clearest. Use the "Photo" column to indicate which photo you extracted the data from. In the Notes column, you may add "Also visible in photo X" for traceability, but do NOT create a second row. Use close-ups for data extraction, overviews for validation: Extract detailed SKU information (brand, flavor, claims, price, ml) from close-up photos where labels are clearest. Use overview photos to cross-check that you haven't missed any SKUs and haven't counted any SKU twice. Facings count: The facings count should reflect the total number of facings for that SKU on the shelf — as seen in the overview photo. Do not sum facings from multiple close-ups.

General Quality Checks
Double-check each SKU against both price tag AND product label: For every SKU entry, validate the data by cross-referencing two sources: Price tag (shelf label): the primary source for price, size, and product identification. Product label (on the bottle/pack itself): the primary source for brand, flavour, claims, and product name. Use both sources to confirm: (a) the brand is correct, (b) the flavor/product name is accurate, and (c) the packaging size matches. If there is a discrepancy, follow the data source hierarchy in STEP 1 and note the conflict in the Notes column. Photos are the primary source: Only include data that is clearly visible in the photos. Minimum confidence for inclusion = 60%. Uncertainties: If something is not clearly visible due to photo angle, shadow, reflection, or distance — assign a lower confidence score and note the issue. Do NOT guess or fabricate prices, sizes, or facings counts — leave blank or default to 1 for facings. Transcript conflicts: If the transcript says something different from what the photo shows → the photo wins. Note the conflict in the Notes column. Missing information: Leave the field blank or use the appropriate default value. Do not guess or fabricate data. ⚡ Juice Extraction Method: If you cannot determine from label or transcript, default to "NA/Centrifugal". ⚡ Processing Method: If you cannot determine from label or transcript, default to "Pasteurised". Use British spelling: "Pasteurised" not "Pasteurized". HPP Treatment: If there is no visible HPP claim on label or in transcript, output "No". Product Type classification: If a product could fit multiple segments (e.g., a protein smoothie), classify by the primary positioning visible on the label. Use Need State to capture the functional aspect. Need State classification (Indulgence vs. Functional): This is an AI assessment. Look for: Functional indicators: Health claims on label, added vitamins/minerals, protein content, fiber, probiotics, superfoods, "boost", "immunity", "energy", functional ingredients like ginger, turmeric, chia, spirulina. Indulgence indicators: Emphasis on taste, fruit imagery, no health claims, classic flavor combinations, "pure", "100% fruit" without added functional ingredients. When in doubt, default to Indulgence. Price per liter: Calculate as price_eur / (packaging_size_ml / 1000). Set to null if price or ml is unknown. Do not count depth: Only count products in the front row. Photo angles may show items stacked behind the front row — ignore these. Facings = horizontal count of front-row items only.

OUTPUT FORMAT — CRITICAL

Your ENTIRE response must be a single valid JSON array. No markdown, no tables, no commentary, no explanation — ONLY the JSON array.

Each element is one SKU object. Use EXACTLY these keys (snake_case):
"photo", "shelf_levels", "shelf_level", "product_type", "branded_private_label", "brand", "sub_brand", "product_name", "flavor", "facings", "price_local", "currency", "price_eur", "packaging_size_ml", "price_per_liter_eur", "need_state", "juice_extraction_method", "processing_method", "hpp_treatment", "packaging_type", "claims", "bonus_promotions", "stock_status", "est_linear_meters", "fridge_number", "confidence_score", "notes"

Data type rules:
- "shelf_levels" and "facings": integers (e.g., 6, 3)
- "packaging_size_ml": integer in milliliters (e.g., 1000, 750)
- "price_local", "price_eur", "price_per_liter_eur", "est_linear_meters": numbers or null (e.g., 1.75, null)
- "confidence_score": integer from 0 to 100 (e.g., 90, 75, 60) — NOT a string like "90%"
- All other fields: strings (use "" for empty/unknown values)

You do NOT need to include "country", "city", "retailer", "store_format", "store_name", or "shelf_location" — these are filled in automatically from user metadata.

Group SKUs by photo (all SKUs from photo 1, then photo 2, etc.). Each unique SKU appears only ONCE.

Example (2 SKUs):

[{{"photo": "foto_1.jpg", "shelf_levels": 6, "shelf_level": "1st", "product_type": "Pure Juices", "branded_private_label": "Private Label", "brand": "The Juice Company", "sub_brand": "", "product_name": "Orange Juice Smooth", "flavor": "Orange", "facings": 3, "price_local": 1.75, "currency": "GBP", "price_eur": null, "packaging_size_ml": 1000, "price_per_liter_eur": null, "need_state": "Indulgence", "juice_extraction_method": "Squeezed", "processing_method": "Pasteurised", "hpp_treatment": "No", "packaging_type": "PET bottle", "claims": "Not From Concentrate", "bonus_promotions": "", "stock_status": "In Stock", "est_linear_meters": null, "fridge_number": "", "confidence_score": 90, "notes": ""}}, {{"photo": "foto_1.jpg", "shelf_levels": 6, "shelf_level": "2nd", "product_type": "Smoothies", "branded_private_label": "Branded", "brand": "Innocent", "sub_brand": "", "product_name": "Strawberry & Banana", "flavor": "Strawberry & Banana", "facings": 2, "price_local": 2.99, "currency": "GBP", "price_eur": null, "packaging_size_ml": 750, "price_per_liter_eur": null, "need_state": "Indulgence", "juice_extraction_method": "NA/Centrifugal", "processing_method": "Pasteurised", "hpp_treatment": "No", "packaging_type": "PET bottle", "claims": "", "bonus_promotions": "", "stock_status": "In Stock", "est_linear_meters": null, "fridge_number": "", "confidence_score": 85, "notes": ""}}]

REMEMBER: Output ONLY the JSON array. Do not wrap it in markdown code fences. Do not add any text before or after the JSON.
"""
