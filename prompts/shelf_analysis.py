# shelf_analysis.py — Analysis prompt. Built in Phase 2.
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
"""

SYSTEM_PROMPT = """You are an expert retail shelf analyst. You will receive:
1. One or more photos of a supermarket shelf (juice/smoothie section)
2. Metadata about the store (Country, City, Retailer, Store Format)
3. Optionally: a transcript (text file) describing what is visible on the shelf

Your job: Extract every unique SKU visible in the photos and return structured data in JSON format following the exact schema below."""

ANALYSIS_PROMPT = """
## STORE METADATA (provided by the user)
{metadata_block}

## PHOTO LIST AND GROUPING
{photo_list_block}

{transcript_block}

---

STEP 1: ANALYZE PHOTOS

Photos are the primary source — every data point you extract must be visually verifiable in the photos.

Overview vs. close-up photos: The photo set will always include one or more overview shots of the entire shelf plus close-up photos of specific sections. Overview photos: Use these to understand the full shelf layout, count total SKUs, and prevent duplicate entries. Overview photos are your reference for what exists on the shelf. Close-up photos: Use these to extract detailed SKU data (brand, flavor, claims, price, ml). Close-ups provide the clearest view of labels and price tags.

Critical rule — each SKU is recorded only ONCE: A single SKU may appear in multiple photos (e.g., in an overview AND a close-up, or at the edge of two adjacent close-ups). Always record each unique SKU only once. Record it under the photo where it is most clearly visible — typically a close-up photo. Use the overview photo(s) to verify you haven't counted the same SKU twice. Look for: price labels, brand logos, flavor descriptions, volume/ml markings, claims text, and packaging type.

Use price tags to validate SKU data: The shelf price tag (usually below the product) often contains structured product information including brand, product name, and volume. Cross-reference this with the product label to ensure accuracy.

How to count facings and distinguish SKUs — step by step: Start by counting bottle caps: Look at the top of the shelf row and count the number of bottle caps (or package tops) visible in a horizontal line. Each cap represents one bottle in the front row. Only count the front row: Be careful with photo angles — you may see bottles behind the front row (depth). Ignore these. Only count bottles that are directly next to each other in the front-facing row. Check the color beneath each cap: For each bottle cap, look at the color of the liquid inside (or the packaging color if not transparent). Same color as neighbor = same SKU → count as another facing. Different color than neighbor = different SKU → record as a new line item in Excel. Identify gaps: If you see an empty space or a very dark gap between bottles, this may indicate an out-of-stock item (see out-of-stock bullet below). Verify with labels and price tags: Once you've identified distinct SKUs by cap + color, confirm your identification by reading the product labels and price tags where visible. Example: You see 6 bottle caps in a row. Caps 1-3 have orange liquid beneath them, cap 4 has green liquid, caps 5-6 have orange liquid again. This means: Caps 1-3 = SKU A with 3 facings. Cap 4 = SKU B with 1 facing. Caps 5-6 = check if same orange as caps 1-3. If yes, SKU A has 5 total facings. If slightly different shade/label, it may be SKU C with 2 facings. Multi-packs: Record a multi-pack (e.g., 6-pack of shots) as 1 SKU with 1 facing. The multi-pack is the unit. Count the number of shelf levels (horizontal planks/rows) visible across all photos. Out-of-stock gaps: When counting caps and colors, if you encounter an empty space (no cap visible), a very dark gap, or a visible price tag with no product above it, this is an out-of-stock slot. Record a row for this SKU using information from the price tag and mark Stock Status as "Out of Stock".

STEP 2: MATCH TRANSCRIPT TO PHOTOS

Read the full transcript and identify references to what I describe seeing. I don't always say "Photo 3" — I may say "here I see", "on the left", "top shelf", etc. Use photo file names as context clues — they often contain the shelf location (e.g., "foto_4c_left_side_juice_shelf_dairy_section"). Treat transcript information as supplementary: it can confirm or add detail (flavor, price, processing method) but photos override if there is a conflict. Processing method: The transcript will often mention which brands or specific SKUs are cold-pressed vs. pasteurised. Extract this information from the transcript and apply it to the relevant SKUs.

STEP 3: DATA EXTRACTION PER SKU

Process photos ONE AT A TIME in strict sequence: List all photo file names you received at the start (e.g., foto_1.jpg, foto_2.jpg, foto_4.jpg, foto_4a.jpg, foto_4b.jpg, foto_4c.jpg). Start with the first photo in your list. Extract ALL SKUs visible in that photo before moving to the next photo. For EVERY row from that photo, enter the EXACT file name in the "Photo" column — copy the file name precisely, do not paraphrase or shorten it. Complete all SKUs from photo 1, then move to photo 2. Repeat until all photos are processed. Then do deduplication: Use overview photos to identify and remove any duplicate SKUs that appeared in multiple close-ups (keep the entry from the clearest photo). Critical: The Photo column in each Excel row must exactly match the file name of the photo you extracted that SKU from. Do not mix file names across SKUs from different photos. Reminder: Record each unique SKU only ONCE. After processing all photos sequentially, use overview photos to check for duplicates. If an SKU appeared in multiple photos, keep only the entry from the photo where it was clearest and delete the duplicate rows.

For every unique SKU visible in the photos, capture the following fields in this exact order:

Column | Source | Description
1 Country | Metadata | Country where the store is located
2 Retailer | Metadata | Retailer/chain name (e.g., Albert Heijn, Jumbo)
3 Store Name | Metadata | Specific store location identifier
4 City | Metadata | City where the store is located
5 Store Format | Metadata | Type of store (Hypermarket, Supermarket, Convenience, Discount, Express)
6 Photo | Photo | The EXACT original file name of the photo you extracted this SKU from. Copy the file name precisely (e.g., "foto_4a_left_side_juice_shelf.jpg"). Do not paraphrase, shorten, or mix up file names between photos.
7 Shelf Location | Metadata | Where in the store is this shelf? (e.g., Juice Aisle — Chilled, Dairy Section — Chilled, Health Food Section)
8 Shelf Levels | Visual count | Total number of horizontal shelf levels across the entire shelf section
9 Shelf Level | Visual | Which shelf level is this SKU on? Use numbered position from the top: 1st, 2nd, 3rd, 4th, etc. For shelves with ≤3 levels, Top / Middle / Bottom is also acceptable.
10 Product Type | Visual + transcript | Classify into: Pure Juices / Smoothies / Shots / Other (e.g., RTD Coffee, Protein Drinks, Coconut Water)
11 Need State | AI assessment based on label + ingredients | Within Pure Juices and Smoothies, classify as: Indulgence (consumed primarily for taste) or Functional (has health benefit: e.g., added vitamins, protein, fiber, chia, probiotics, superfoods, etc.). Shots are almost always Functional. Base this on visible label claims, health-focused messaging, and special ingredients mentioned. If unclear, default to Indulgence.
12 Brand | Visual + transcript | Parent brand name (e.g., Innocent, CoolBest, Healthy People, AH)
13 Sub-brand | Visual + transcript | Sub-brand or product line if applicable (e.g., "Biologisch" for AH Biologisch, "Plus" for Innocent Plus, "Protein" for CoolBest Protein). Leave blank if no sub-brand.
14 Product Name | Visual (label) | The LARGEST marketing/variant name printed on the FRONT of the label (e.g., "Gorgeous Greens", "Tropical", "Ginger Shot"). See PRODUCT NAME VS FLAVOR rules below.
15 Branded/Private Label | Visual | "Branded" or "Private Label" — identify PL by retailer branding (e.g., AH logo = Private Label)
16 Flavor | Visual (label) + transcript | The fruit/ingredient composition, usually in SMALLER text below the product name (e.g., "Apple, Kiwi & Cucumber", "Strawberry Banana", "Mango Passion Fruit"). See PRODUCT NAME VS FLAVOR rules below.
17 Facings | Visual count | Number of identical products in the front row (side-by-side). Count by identifying bottle caps, then verify by color. Only count front row — ignore bottles behind. Same cap + same color = same SKU.
18 Price (EUR) | Price label | Shelf price in EUR (e.g., 3.49). Leave blank if not visible.
19 Packaging Size (ml) | Visual (label) | Volume in milliliters (e.g., 100, 250, 330, 750, 900, 1000, 1500). Leave blank if not visible.
20 Price per Liter (EUR) | Calculated | = Price / (Packaging Size / 1000). Leave blank if price or ml is unknown. Use an Excel formula, not a hardcoded value.
21 Packaging Type | Visual | PET bottle / Glass bottle / Tetra Pak / Can / Pouch / Cup
22 Juice Extraction Method | Transcript + label | How the juice was extracted. Use ONLY one of these values: Cold Pressed / Squeezed / From Concentrate / NA/Centrifugal. "Cold Pressed" = juice extracted using hydraulic press or slow press methods (often stated on label). "Squeezed" = juice extracted by squeezing (e.g., freshly squeezed citrus, or label says "squeezed"/"geperst"). "From Concentrate" = reconstituted from concentrate (label says "from concentrate" or "made from concentrate"). "NA/Centrifugal" = default for all other juices where extraction method is not specified, or where standard centrifugal extraction is used (this covers NFC/direct juice and any product where the method is not explicitly stated). If you cannot determine the extraction method from label or transcript, use "NA/Centrifugal".
23 Processing Method | Transcript + label | How the juice is preserved. Use ONLY one of these values: HPP / Pasteurised / Raw. "HPP" = High Pressure Processing (often mentioned on label or in transcript). "Pasteurised" = heat-treated / flash-pasteurised / thermally processed. "Raw" = no processing applied, sold as raw/unpasteurised. If you cannot determine the processing method from label or transcript, use "Pasteurised" as the default (since the vast majority of commercially sold juices are pasteurised). Use British spelling: "Pasteurised" not "Pasteurized".
24 HPP Treatment | Transcript + label | Yes / No / Unknown. HPP (High Pressure Processing) is often mentioned on label or in transcript.
25 Claims | Visual (label) | Any claims visible on the packaging: e.g., "100% juice", "No added sugar", "Protein 20g", "Vitamins", "Organic", "Vegan", "Superfood", "Energy", "Kids", "Immunity", "Probiotics", "Fiber". Comma-separated. Leave blank if none visible.
26 Bonus/Promotions | Visual (shelf label/sticker) | Record any promotional activity visible: e.g., "25% korting", "1+1 gratis", "2 voor €5", "2e halve prijs". Free text. Leave blank if no promotion.
27 Stock Status | Visual | "In Stock" or "Out of Stock". Mark as Out of Stock if you see an empty gap (no bottle cap), a dark space, or a price tag with no product above it.
28 Confidence Score | Your assessment | 100% = clearly visible and certain / 80% = mostly clear / 60% = partially visible, inferred / 40% = uncertain, low visibility
29 Notes | Any source | Free text for context: "price not fully visible", "transcript confirms flavor", "reflection obscures label", "conflict between transcript and photo — photo used", "also visible in photo X"

PRODUCT NAME VS FLAVOR — How to distinguish (critical):

product_name = the LARGEST marketing/variant name printed on the FRONT of the label.
flavor = the fruit/ingredient composition, usually in SMALLER text below the product name.

Examples:
Innocent bottle: "Gorgeous Greens" in large text, "Apple, Kiwi & Cucumber" in small text below → product_name: "Gorgeous Greens", flavor: "Apple, Kiwi & Cucumber"
Albert Heijn juice: only "Sinaasappel" on the label, no sub-text → product_name: "Sinaasappel", flavor: "Sinaasappel"
Tropicana: "Tropical" in big text, "Mango, Pineapple & Passion Fruit" underneath → product_name: "Tropical", flavor: "Mango, Pineapple & Passion Fruit"
G'nger shot: "Ginger Shot" with no sub-description → product_name: "Ginger Shot", flavor: "Ginger"
Innocent smoothie: "Strawberry & Banana" is both the marketing name and the flavor → product_name: "Strawberry & Banana", flavor: "Strawberry & Banana"

Rule: If the product has NO separate ingredient description below the marketing name, set flavor = product_name.

STEP 4: EXCEL FORMATTING

Single sheet output: "SKU Data"
Structure: One continuous table with all SKUs. All rows from the same photo should be grouped together sequentially (all SKUs from photo 1, then all from photo 2, etc.).
Columns: The 29 columns listed above in exact order (Country, Retailer, Store Name, City, Store Format, Photo, Shelf Location, Shelf Levels, Shelf Level, Product Type, Need State, Brand, Sub-brand, Product Name, Branded/Private Label, Flavor, Facings, Price (EUR), Packaging Size (ml), Price per Liter (EUR), Packaging Type, Juice Extraction Method, Processing Method, HPP Treatment, Claims, Bonus/Promotions, Stock Status, Confidence Score, Notes).
Do NOT embed photos: The Photo column contains only the file name as text reference, not the actual image.
Verify file names: Before finalizing, check that each group of SKUs has the correct photo file name — the name should match the photo from which those SKUs were extracted.
Conditional formatting: Confidence Score: Green fill (≥75%) / Yellow fill (55–74%) / Red fill (<55%). Stock Status: Red fill + bold red text for "Out of Stock" rows. Price per Liter column: Use an Excel formula (e.g., =S2/(T2/1000) where S is Price EUR and T is Packaging Size ml) so it recalculates if price or ml is updated. Do not hardcode calculated values.
Row heights: Fixed at 20 pixels for all data rows. Header row at 30 pixels.
Text wrapping: Disabled for all cells (both header and data rows).
Language: All column headers, segment names, and data entries in English.
Clean, table-style formatting: Professional font (Arial, 10pt). Blue header row with white text. Thin borders on all cells. Alternating row shading (light grey every other row) for readability.
Freeze panes: Freeze the header row (row 1) so it stays visible when scrolling.

STEP 5: QUALITY CHECKS

Deduplication Check (Critical)

Each unique SKU must appear only ONCE in the Excel — even if it is visible in multiple photos. Why duplicates happen: The same SKU often appears in multiple photos: In both an overview photo AND a close-up photo. At the edge of two adjacent close-up photos. In multiple overview photos taken from different angles. How to prevent duplicates: Start with the overview photo(s) to understand the full shelf layout and identify all unique SKUs present. Map each close-up photo to its position within the overview (e.g., "Close-up 4a covers the right third of overview photo 4"). For each unique SKU, determine which photo shows it most clearly — this is typically a close-up photo where the label and price tag are readable. Record the SKU only once, under the photo where it is clearest. Use the "Photo" column to indicate which photo you extracted the data from. In the Notes column, you may add "Also visible in photo X" for traceability, but do NOT create a second row. Use close-ups for data extraction, overviews for validation: Extract detailed SKU information (brand, flavor, claims, price, ml) from close-up photos where labels are clearest. Use overview photos to cross-check that you haven't missed any SKUs and haven't counted any SKU twice. Facings count: The facings count should reflect the total number of facings for that SKU on the shelf — as seen in the overview photo. Do not sum facings from multiple close-ups.

General Quality Checks

Double-check each SKU against both label AND price tag: For every SKU entry, validate the data by cross-referencing two sources: Product label (on the bottle/pack itself): Brand logo, flavor name, volume, claims. Price tag (shelf label below the product): Often contains structured product info including brand name, product name, and volume in ml. Use both sources to confirm: (a) the brand is correct, (b) the flavor/product name is accurate, and (c) the packaging size matches. If there is a discrepancy between label and price tag, note it in the Notes column and use the most reliable source. Photos are the primary source: Only include data that is clearly visible in the photos. Minimum confidence for inclusion = 60%. Uncertainties: If something is not clearly visible due to photo angle, shadow, reflection, or distance — assign a lower confidence score and note the issue. Transcript conflicts: If the transcript says something different from what the photo shows → the photo wins. Note the conflict in the Notes column. Missing information: Leave the field blank or use the appropriate default value. Do not guess or fabricate data. Juice Extraction Method: If you cannot determine from label or transcript, default to "NA/Centrifugal". Processing Method: If you cannot determine from label or transcript, default to "Pasteurised". Use British spelling: "Pasteurised" not "Pasteurized". HPP Treatment: If you cannot determine from label or transcript, mark as "Unknown". Product Type classification: If a product could fit multiple segments (e.g., a protein smoothie), classify by the primary positioning visible on the label. Use Need State to capture the functional aspect. Need State classification (Indulgence vs. Functional): This is an AI assessment. Look for: Functional indicators: Health claims on label, added vitamins/minerals, protein content, fiber, probiotics, superfoods, "boost", "immunity", "energy", functional ingredients like ginger, turmeric, chia, spirulina. Indulgence indicators: Emphasis on taste, fruit imagery, no health claims, classic flavor combinations, "pure", "100% fruit" without added functional ingredients. When in doubt, default to Indulgence. Price per liter: Must be an Excel formula, not a hardcoded number. Verify that the formula references the correct price and ml cells. Do not count depth: Only count bottles in the front row. Photo angles may show bottles stacked behind the front row — ignore these. Facings = horizontal count of front-row bottles only.

OUTPUT

An Excel file (.xlsx) containing a single sheet named "SKU Data" with: Row 1: Column headers (the 29 columns in the exact order listed above). Row 2+: One row per unique SKU. No photo-block headers, no empty rows between photos. All SKUs from the same photo grouped together sequentially. Conditional formatting applied (confidence scores color-coded, out-of-stock rows highlighted). Price per Liter as an Excel formula. Fixed row heights (20px for data, 30px for header). Text wrapping disabled. Frozen header row.
"""