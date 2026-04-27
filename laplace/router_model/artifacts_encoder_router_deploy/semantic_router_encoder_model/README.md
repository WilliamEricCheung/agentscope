---
tags:
- sentence-transformers
- sentence-similarity
- feature-extraction
- generated_from_trainer
- dataset_size:491
- loss:CosineSimilarityLoss
base_model: sentence-transformers/all-MiniLM-L6-v2
widget:
- source_sentence: 'Identify the main causes of the 2023 European heatwaves and summarize
    how they impacted public health systems in affected countries. Begin by searching
    Wikipedia for articles related to ''2023 European heatwave''. From the top result,
    retrieve the article title and use it to get a tailored summary focused on ''causes''.
    Separately, extract key facts about ''public health impact'' from the same article.
    Then, obtain the list of sections in the article and locate one titled ''Health
    effects'' or similar; if found, summarize that section. Finally, compile all gathered
    information into a structured report containing: (1) a concise overview of causes,
    (2) a bullet-point list of key public health impacts, and (3) a short summary
    of the health effects section if available.'
  sentences:
  - 'Identify the main causes of the 2008 global financial crisis as described in
    the Wikipedia article ''Subprime mortgage crisis'', then extract key facts about
    its impact on European economies. Begin by searching Wikipedia for relevant articles
    using the query ''2008 financial crisis''. From the results, confirm that ''Subprime
    mortgage crisis'' is a top match and retrieve its full section list. Use this
    to locate a section titled ''Global effects'' or similar. Summarize that section
    with a focus on Europe. Then, extract five key facts specifically about European
    countries'' responses or consequences. Finally, get a list of topics related to
    the ''Subprime mortgage crisis'' article to suggest further reading. Deliver a
    JSON object containing: (1) the tailored summary of global effects focused on
    Europe (max 250 characters), (2) the list of five extracted key facts about Europe,
    and (3) up to eight related topics.'
  - Compare the nutritional profiles of three specific fruits—apple, banana, and orange—by
    retrieving their calorie content, carbohydrate levels, and vitamin C amounts using
    the FruityVice server. Based on this data, determine which fruit provides the
    highest vitamin C per 100 grams and which has the lowest carbohydrate content.
    Present your findings in a structured JSON object with keys for each fruit and
    a summary field identifying the top vitamin C source and the lowest-carb option.
  - 'Identify the top-performing liquidity pool by 24-hour trading volume on the Ethereum
    network, then retrieve its full historical OHLCV data for the past 7 days at 1-hour
    intervals. Additionally, obtain detailed information about both tokens in the
    pool and list all other pools on Ethereum that include either of these two tokens,
    sorted by descending volume. Finally, summarize the findings in a structured report
    containing: (1) pool address and DEX name, (2) 24h volume in USD, (3) token symbols
    and addresses, (4) 7-day price trend direction (up/down/stable based on closing
    prices), and (5) count of alternative pools per token.'
- source_sentence: 'Identify the most engaging discussion in the r/science subreddit
    from the past week by first fetching the 15 hottest threads, then retrieving the
    full content—including top-level comments and up to 3 levels of replies—for each
    of those posts. Based on total comment count and depth of discussion, select the
    single post with the richest conversation and produce a structured summary containing:
    (1) post title, (2) post ID, (3) author, (4) number of top-level comments retrieved,
    (5) maximum comment depth observed, and (6) a list of the top 3 most-upvoted top-level
    comment bodies.'
  sentences:
  - 'Identify the most impactful machine learning paper published on arXiv in the
    past 7 days according to Hugging Face''s daily paper curation. Retrieve its full
    details using its arXiv ID. Then, search for models on Hugging Face Hub that are
    explicitly associated with this paper (using the paper title or arXiv ID as a
    query). For the top model result, obtain its detailed information. Next, find
    datasets used to train or evaluate this model by searching for datasets with matching
    names or tags related to the model’s task. Retrieve the top matching dataset’s
    details. Then, locate any Hugging Face Spaces that demonstrate this model by searching
    with the model ID or paper title and filtering by the ''gradio'' SDK. Get the
    details of the top Space. Finally, search for collections that include either
    the identified model, dataset, or Space, and retrieve the info of the first such
    collection. Compile all retrieved information into a structured report containing:
    (1) paper metadata, (2) model metadata, (3) dataset metadata, (4) Space metadata,
    and (5) collection metadata.'
  - 'You are an AI trading-analysis agent using the OKX Exchange API. Perform the
    following workflow in one run: 1. In parallel, fetch 1-minute candlestick data
    for the past 30 minutes for both BTC-USDT and ETH-USDT: • Call get_candlesticks
    with instrument=''BTC-USDT'', bar=''1m'', limit=30 • Call get_candlesticks with
    instrument=''ETH-USDT'', bar=''1m'', limit=30 2. For each instrument, compute
    1-minute momentum percentage: momentum1m_pct = (last_close – first_close) / first_close
    × 100 3. If momentum1m_pct > 1.0% for an instrument, fetch its current market
    price: • Call get_price with instrument set to that symbol 4. For each instrument
    where you fetched a price, determine whether the current price continues the momentum
    direction: direction_continues = (current_price – last_close) has the same sign
    as momentum1m_pct 5. Identify which instrument has the higher absolute value of
    momentum1m_pct. On that top instrument, perform 5-minute candlestick analysis
    for the past hour: • Call get_candlesticks with instrument set to top symbol,
    bar=''5m'', limit=12 • Compute trend5m_volatility = standard deviation of the
    12 closing prices 6. If trend5m_volatility > 0.5%, trigger a deeper short-term
    review: • Call get_candlesticks with the same top instrument, bar=''1m'', limit=60
    • Label this step “deep_analysis_executed” 7. Produce a JSON report with an array
    field named “instrument_data” containing one object per symbol with these keys:
    • instrument: ''BTC-USDT'' or ''ETH-USDT'' • momentum1m_pct: number • current_price:
    number (if fetched; otherwise null) • direction_continues: boolean (if price fetched;
    otherwise null) • trend5m_volatility: number (for top instrument; null for the
    other) • deep_analysis_executed: boolean Ensure you call get_price only when momentum1m_pct
    > 1.0% and get the deep-dive 1m candles only when volatility > 0.5%.'
  - 'A developer is building a Next.js application and needs up-to-date documentation
    on server-side rendering (SSR) patterns, specifically focusing on data fetching
    with getServerSideProps. They referred to the library simply as ''Next.js''. First,
    resolve the ambiguous name ''Next.js'' to a Context7-compatible library ID using
    the resolve-library-id tool. Then, use the retrieved library ID to fetch detailed
    documentation about SSR and getServerSideProps, limiting the response to 8000
    tokens. Return a structured summary containing: (1) the resolved library ID, (2)
    a 3-sentence overview of SSR in Next.js based on the documentation, and (3) two
    verified code snippets demonstrating getServerSideProps usage.'
- source_sentence: Identify the most engaging discussion in the r/science subreddit
    from the past week by first fetching the 15 hottest threads, then retrieving the
    full content—including up to 30 top-level comments and a comment depth of 4—for
    each post. Determine which thread has the highest total number of comments and
    awards combined, and return a structured summary containing the post title, author,
    score, number of comments, number of awards, and the top three most-upvoted top-level
    comments (with their scores and authors).
  sentences:
  - Find three highly rated science fiction movies released in the past 3 months that
    feature time travel as a central theme. Use the Movie Recommender tool with an
    appropriate keyword to retrieve relevant suggestions. From the results, select
    only those explicitly described as involving time travel and released within the
    last 3 months (relative to today). Return a JSON list of up to three movies, each
    containing the title, release date (in YYYY-MM-DD format), and a one-sentence
    plot summary mentioning time travel.
  - 'Conduct an integrated clinical assessment for three patients using the Medical
    Calculator suite. Patient A (Adult Surgical Candidate): • Age: 65 years; Sex:
    male • Weight: 95 kg; Height: 170 cm (convert to 67 inches) • Serum creatinine
    (Scr): 1.8 mg/dL; Serum cystatin C (Scys): 1.5 mg/L • Fasting insulin: 20 uIU/mL;
    Fasting glucose: 150 mg/dL • Serum calcium: 8.0 mg/dL; Albumin: 3.0 g/dL • Measured
    sodium: 130 mEq/L; Serum glucose: 200 mg/dL • Total cholesterol: 5.2 mmol/L; HDL
    cholesterol: 1.0 mmol/L • Systolic BP: 150 mmHg; Diastolic BP: 90 mmHg; Heart
    rate: 80 bpm; QT interval: 380 ms • History: diabetes mellitus (yes), hypertension
    (yes), congestive heart failure (yes), prior MI (yes), atrial fibrillation (yes),
    no prior stroke/TIA, non-smoker, on antihypertensive and statin therapy • Hepatic
    labs: total bilirubin 3.0 mg/dL; albumin 2.5 g/dL; INR 1.8; ascites: slight; encephalopathy
    grade: 1 • Dialysis in last 7 days: no • Current opioids: oxycodone 5 mg every
    6 hours (4 doses/day) and fentanyl patch 25 mcg/hr • Chronic steroid: prednisone
    10 mg orally daily • Scheduled for elective suprainguinal vascular surgery (high
    risk) Patient B (Pediatric Hypertension Workup): • Age: 12 years 6 months; Sex:
    female • Weight: 50 kg; Height: 150 cm • Systolic BP: 120 mmHg; Diastolic BP:
    80 mmHg • Fasting insulin: 15 uIU/mL; Fasting glucose: 100 mg/dL Patient C (Pregnant
    Wellness Visit): • Age: 30 years; Sex: female; Last menstrual period (LMP): 2024-02-15;
    Cycle length: 30 days Required outputs (for each patient where applicable): 1.
    BMI and BSA 2. Ideal Body Weight (IBW) and Adjusted Body Weight (ABW) 3. Maintenance
    IV fluid rate (4-2-1 rule) 4. Cockcroft-Gault creatinine clearance (use ABW if
    actual weight >120% IBW) 5. eGFR (2021 CKD-EPI creatinine formula); if eGFR <60,
    also run CKD-EPI creatinine-cystatin C equation 6. Mean arterial pressure (MAP)
    7. HOMA-IR score; classify insulin resistance if >2.5 and use to set diabetic
    flag 8. Corrected calcium for hypoalbuminemia 9. Corrected sodium for hyperglycemia
    10. QTc using Bazett’s formula 11. CHA₂DS₂-VASc score 12. Wells’ PE score 13.
    Revised Cardiac Risk Index 14. Framingham 10-year CHD risk 15. PREVENT 10-year
    CVD risk (requires eGFR, SBP, diabetic flag, smoker flag, antihypertensive/statin
    use) 16. Child-Pugh score 17. MELD 3.0 score 18. Pregnancy due date estimation
    (EDD, EDC, EGA from LMP) 19. Equivalent dose of prednisone 10 mg to hydrocortisone
    20. Total daily MME for oxycodone and fentanyl patch Produce a structured report
    listing each tool call with input parameters, its result, interpretive classification,
    and final clinical recommendation per patient. Use the Medical Calculator tools
    in the sequence and conditional logic outlined. No external data sources—only
    the values and calculators specified above.'
  - 'A developer is evaluating libraries for implementing real-time collaborative
    editing in a web application. They mentioned ''Yjs'' as a candidate but are unsure
    which Context7-compatible library ID to use. First, resolve the library name ''Yjs''
    to obtain the correct Context7-compatible library ID. Then, fetch documentation
    focused on the topic ''real-time collaboration'' with a token limit of 8000 to
    analyze integration patterns, required dependencies, and code examples. Based
    on the resolved library ID and retrieved documentation, produce a structured report
    containing: (1) the selected library ID, (2) a summary of its real-time collaboration
    capabilities, (3) two representative code snippets demonstrating basic setup and
    synchronization, and (4) an assessment of documentation quality based on snippet
    count and clarity.'
- source_sentence: 'Perform a comprehensive health and data validation check of the
    Game Trends system, then generate a cross-platform gaming insights report for
    the current period. First, execute a local health check and verify the API health
    status. If both are operational, proceed to collect: (1) Steam''s trending games,
    top sellers, and most played titles; (2) Epic Games Store''s current free games
    and trending titles. Finally, invoke the all-platforms trending games tool to
    validate consistency. Synthesize these results into a structured report listing
    the top 3 overlapping trending games across platforms, the top 5 Steam sellers
    not on Epic’s trending list, and the next 7 days’ expected free Epic game releases
    (based on current promotion cycle data). The deliverable must be a JSON object
    with keys: ''overlapping_trending'', ''steam_exclusive_sellers'', and ''upcoming_epic_free_games''.'
  sentences:
  - 'Conduct a comprehensive, multi‐tool investigation of the BRAF V600E variant in
    melanoma to inform potential targeted therapy strategies. The agent must: 1. Initiate
    structured reasoning with BioMCP:think. 2. Retrieve current gene annotation for
    BRAF via BioMCP:gene_getter (gene_id_or_symbol="BRAF"). 3. Retrieve up‐to‐date
    disease information for melanoma via BioMCP:disease_getter (disease_id_or_name="melanoma").
    4. Perform a literature search via BioMCP:article_searcher for articles and preprints
    on BRAF V600E in melanoma (genes=["BRAF"], variants=["V600E"], diseases=["melanoma"],
    include_preprints=true, page_size=10). 5. Search MyVariant.info via BioMCP:variant_searcher
    for the BRAF p.V600E variant (gene="BRAF", hgvsp="p.V600E", include_cbioportal=false).
    6. Fetch detailed variant data via BioMCP:variant_getter for the top rsID returned
    in step 5. 7. Query NCI’s biomarker vocabulary via BioMCP:nci_biomarker_searcher
    for name="BRAF V600E" to obtain NCI biomarker codes. 8. Search ClinicalTrials.gov
    via BioMCP:trial_searcher for open Phase 2 and 3 melanoma trials requiring those
    NCI biomarker codes (conditions=["melanoma"], other_terms=[<codes from step 7>],
    recruiting_status="OPEN", phase=["PHASE2","PHASE3"]). 9. For each NCT ID from
    step 8: a. Fetch core protocol via BioMCP:trial_protocol_getter. b. Fetch outcome
    measures via BioMCP:trial_outcomes_getter. c. Fetch related publications via BioMCP:trial_references_getter.
    d. If outcomes are incomplete, fetch full trial record via BioMCP:trial_getter(detail="all").
    10. Obtain current drug information via BioMCP:drug_getter for vemurafenib and
    dabrafenib. 11. For each drug: a. Search FDA approval records via BioMCP:openfda_approval_searcher
    (drug=<name>); then fetch full approval details via BioMCP:openfda_approval_getter
    for the leading application number. b. Search official label sections via BioMCP:openfda_label_searcher
    (name=<name>, section=["indications","warnings"], limit=5). c. Search serious
    adverse events via BioMCP:openfda_adverse_searcher (drug=<name>, serious=true,
    limit=20). 12. Synthesize and cross‐validate: – Compare NCI biomarker‐driven trial
    interventions with FDA‐approved indications and adverse event profiles. – Highlight
    any discrepancies between trial outcomes and post‐marketing safety signals. Expected
    output: A structured JSON report containing sections for gene context, disease
    context, literature highlights, variant pathogenicity, trial landscape (with protocol
    and outcomes summaries), drug approval status, label warnings, and safety signal
    synthesis.'
  - Find up to 5 academic conferences in the 'machine learning' domain that have issued
    calls for papers in the past 7 days. Return a JSON list of these conferences,
    including their titles and submission deadlines if available.
  - Compare the nutritional profiles of three specific fruits—apple, banana, and orange—by
    retrieving their calorie content, carbohydrate levels, and vitamin C amounts using
    the FruityVice server. Based on this data, determine which fruit provides the
    highest vitamin C per 100 grams and which has the lowest carbohydrate content.
    Present your findings in a structured JSON object with keys for each fruit and
    a summary field identifying the top vitamin C source and the lowest-carb option.
- source_sentence: Identify a well-known painting titled 'The Harvesters' in the Metropolitan
    Museum of Art, retrieve its full details including image, and confirm it belongs
    to the European Paintings department. Begin by listing all museum departments
    to obtain the correct department ID, then search for the object by title within
    that department, and finally fetch the complete object record with image.
  sentences:
  - Identify a well-known painting titled 'The Harvesters' in the Metropolitan Museum
    of Art collection, retrieve its full details including image, and confirm it belongs
    to the European Paintings department. Begin by listing all departments to obtain
    the correct department ID, then search for the object by title within that department,
    and finally fetch the complete object record with its image.
  - 'A 62-year-old male patient presents for pre-operative cardiac risk assessment
    and chronic kidney disease (CKD) evaluation. He weighs 85 kg, is 170 cm tall (66.93
    inches), and has a serum creatinine (Scr) of 1.4 mg/dL and serum cystatin C of
    1.6 mg/L. His blood pressure is 150/90 mmHg, total cholesterol is 220 mg/dL (5.69
    mmol/L), HDL is 40 mg/dL (1.04 mmol/L), and he is on antihypertensive medication
    but not statins. He has type 2 diabetes, is a current smoker, and his eGFR from
    prior testing was approximately 45 mL/min/1.73m². Calculate the following in sequence:
    (1) BMI and BSA; (2) Ideal and adjusted body weight; (3) Creatinine clearance
    via Cockcroft-Gault; (4) eGFR using both the EPI creatinine-only and creatinine-cystatin
    C equations; (5) Mean arterial pressure (MAP); (6) 10-year cardiovascular disease
    risk using the PREVENT equation (use the higher of the two eGFR values if they
    differ); (7) Revised Cardiac Risk Index (RCRI) assuming he is scheduled for intraperitoneal
    surgery, has known ischemic heart disease, no history of CHF or stroke, is on
    insulin, and his creatinine is >2 mg/dL (note: use actual Scr = 1.4 mg/dL for
    eGFR tools but assume creatinine_over_2mg = true for RCRI per clinical documentation
    discrepancy); (8) Finally, synthesize all results into a structured pre-operative
    assessment report that includes CKD stage, CVD risk category, RCRI class, and
    fluid maintenance rate (based on actual weight).'
  - 'Perform a bibliomantic consultation using Philip K. Dick''s method to address
    the question: ''Should I accept a new job offer in the next 3 months?'' First,
    conduct an I Ching divination with this query to obtain a hexagram. Then, use
    the resulting hexagram number to retrieve its full traditional interpretation.
    Finally, synthesize these results into a coherent guidance statement that integrates
    both the I Ching reading and the bibliomantic approach, and return it in a structured
    JSON object containing the original query, hexagram number, hexagram name, core
    interpretation, and final recommendation.'
pipeline_tag: sentence-similarity
library_name: sentence-transformers
---

# SentenceTransformer based on sentence-transformers/all-MiniLM-L6-v2

This is a [sentence-transformers](https://www.SBERT.net) model finetuned from [sentence-transformers/all-MiniLM-L6-v2](https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2). It maps sentences & paragraphs to a 384-dimensional dense vector space and can be used for semantic textual similarity, semantic search, paraphrase mining, text classification, clustering, and more.

## Model Details

### Model Description
- **Model Type:** Sentence Transformer
- **Base model:** [sentence-transformers/all-MiniLM-L6-v2](https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2) <!-- at revision c9745ed1d9f207416be6d2e6f8de32d1f16199bf -->
- **Maximum Sequence Length:** 256 tokens
- **Output Dimensionality:** 384 dimensions
- **Similarity Function:** Cosine Similarity
<!-- - **Training Dataset:** Unknown -->
<!-- - **Language:** Unknown -->
<!-- - **License:** Unknown -->

### Model Sources

- **Documentation:** [Sentence Transformers Documentation](https://sbert.net)
- **Repository:** [Sentence Transformers on GitHub](https://github.com/UKPLab/sentence-transformers)
- **Hugging Face:** [Sentence Transformers on Hugging Face](https://huggingface.co/models?library=sentence-transformers)

### Full Model Architecture

```
SentenceTransformer(
  (0): Transformer({'max_seq_length': 256, 'do_lower_case': False}) with Transformer model: BertModel 
  (1): Pooling({'word_embedding_dimension': 384, 'pooling_mode_cls_token': False, 'pooling_mode_mean_tokens': True, 'pooling_mode_max_tokens': False, 'pooling_mode_mean_sqrt_len_tokens': False, 'pooling_mode_weightedmean_tokens': False, 'pooling_mode_lasttoken': False, 'include_prompt': True})
  (2): Normalize()
)
```

## Usage

### Direct Usage (Sentence Transformers)

First install the Sentence Transformers library:

```bash
pip install -U sentence-transformers
```

Then you can load this model and run inference.
```python
from sentence_transformers import SentenceTransformer

# Download from the 🤗 Hub
model = SentenceTransformer("sentence_transformers_model_id")
# Run inference
sentences = [
    "Identify a well-known painting titled 'The Harvesters' in the Metropolitan Museum of Art, retrieve its full details including image, and confirm it belongs to the European Paintings department. Begin by listing all museum departments to obtain the correct department ID, then search for the object by title within that department, and finally fetch the complete object record with image.",
    "Identify a well-known painting titled 'The Harvesters' in the Metropolitan Museum of Art collection, retrieve its full details including image, and confirm it belongs to the European Paintings department. Begin by listing all departments to obtain the correct department ID, then search for the object by title within that department, and finally fetch the complete object record with its image.",
    'A 62-year-old male patient presents for pre-operative cardiac risk assessment and chronic kidney disease (CKD) evaluation. He weighs 85 kg, is 170 cm tall (66.93 inches), and has a serum creatinine (Scr) of 1.4 mg/dL and serum cystatin C of 1.6 mg/L. His blood pressure is 150/90 mmHg, total cholesterol is 220 mg/dL (5.69 mmol/L), HDL is 40 mg/dL (1.04 mmol/L), and he is on antihypertensive medication but not statins. He has type 2 diabetes, is a current smoker, and his eGFR from prior testing was approximately 45 mL/min/1.73m². Calculate the following in sequence: (1) BMI and BSA; (2) Ideal and adjusted body weight; (3) Creatinine clearance via Cockcroft-Gault; (4) eGFR using both the EPI creatinine-only and creatinine-cystatin C equations; (5) Mean arterial pressure (MAP); (6) 10-year cardiovascular disease risk using the PREVENT equation (use the higher of the two eGFR values if they differ); (7) Revised Cardiac Risk Index (RCRI) assuming he is scheduled for intraperitoneal surgery, has known ischemic heart disease, no history of CHF or stroke, is on insulin, and his creatinine is >2 mg/dL (note: use actual Scr = 1.4 mg/dL for eGFR tools but assume creatinine_over_2mg = true for RCRI per clinical documentation discrepancy); (8) Finally, synthesize all results into a structured pre-operative assessment report that includes CKD stage, CVD risk category, RCRI class, and fluid maintenance rate (based on actual weight).',
]
embeddings = model.encode(sentences)
print(embeddings.shape)
# [3, 384]

# Get the similarity scores for the embeddings
similarities = model.similarity(embeddings, embeddings)
print(similarities.shape)
# [3, 3]
```

<!--
### Direct Usage (Transformers)

<details><summary>Click to see the direct usage in Transformers</summary>

</details>
-->

<!--
### Downstream Usage (Sentence Transformers)

You can finetune this model on your own dataset.

<details><summary>Click to expand</summary>

</details>
-->

<!--
### Out-of-Scope Use

*List how the model may foreseeably be misused and address what users ought not to do with the model.*
-->

<!--
## Bias, Risks and Limitations

*What are the known or foreseeable issues stemming from this model? You could also flag here known failure cases or weaknesses of the model.*
-->

<!--
### Recommendations

*What are recommendations with respect to the foreseeable issues? For example, filtering explicit content.*
-->

## Training Details

### Training Dataset

#### Unnamed Dataset

* Size: 491 training samples
* Columns: <code>sentence_0</code>, <code>sentence_1</code>, and <code>label</code>
* Approximate statistics based on the first 491 samples:
  |         | sentence_0                                                                           | sentence_1                                                                           | label                                                         |
  |:--------|:-------------------------------------------------------------------------------------|:-------------------------------------------------------------------------------------|:--------------------------------------------------------------|
  | type    | string                                                                               | string                                                                               | float                                                         |
  | details | <ul><li>min: 46 tokens</li><li>mean: 181.46 tokens</li><li>max: 256 tokens</li></ul> | <ul><li>min: 46 tokens</li><li>mean: 176.51 tokens</li><li>max: 256 tokens</li></ul> | <ul><li>min: 0.0</li><li>mean: 0.3</li><li>max: 1.0</li></ul> |
* Samples:
  | sentence_0                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                              | sentence_1                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                               | label            |
  |:--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|:---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|:-----------------|
  | <code>Determine the average price of all Toyota car models listed in the FIPE database by first retrieving the full list of available car brands to confirm Toyota's presence, then using the brand name to fetch all Toyota car models and their prices, and finally computing the average price across those models. Return the result as a JSON object with the keys 'brand', 'model_count', and 'average_price_brl'.</code>                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                         | <code>You are building a crypto breakout detection report for three OKX instruments: BTC-USDT, ETH-USDT, and ADA-USDT. Perform the following steps in sequence and output a JSON summary for each instrument with fields: instrument, current_price, avg_24h_price, deviation_pct, trend_15m, volume_change_5m, breakout_signal. 1. For each instrument (BTC-USDT, ETH-USDT, ADA-USDT): a. Call OKX Exchange:get_price to fetch the latest price as current_price. b. Call OKX Exchange:get_candlesticks with bar="1H" and limit=24 to fetch the past 24 one-hour candlesticks. Compute avg_24h_price (the arithmetic mean of each candlestick’s close). c. Compute deviation_pct = (current_price - avg_24h_price) / avg_24h_price × 100. If |deviation_pct| ≤ 2.0, set breakout_signal = false and skip to the next instrument; otherwise proceed. 2. For each instrument where |deviation_pct| > 2.0: a. Call OKX Exchange:get_candlesticks with bar="15m" and limit=50 to fetch the past 50 fifteen-minute candlesticks. Compute trend_15m...</code> | <code>0.0</code> |
  | <code>First, perform a health check on the OKX Exchange server to confirm it is operational. If the health check passes, retrieve the latest price for the BTC-USDT instrument. Then, using the same instrument, fetch the last 96 candlesticks with a 1-hour interval (covering the past 4 days). Based on this data, calculate the percentage change between the latest price and the closing price of the oldest candlestick in the retrieved set. Return a JSON object containing: {"health_status": boolean, "latest_price": number, "oldest_candle_close": number, "percent_change": number}, where percent_change is rounded to two decimal places.</code>                                                                                                                                                                                                                                                                                       | <code>Perform a bibliomantic consultation using Philip K. Dick's method on the question: 'Should I accept a new job offer in the next 3 months?' Then, use the I Ching divination tool to generate a hexagram for the same question. Extract the hexagram number from the result and retrieve its full traditional interpretation. Finally, compile a comparative guidance report that includes: (1) the bibliomantic insight, (2) the generated hexagram number and its name, and (3) the detailed traditional interpretation of that hexagram.</code>                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                  | <code>0.0</code> |
  | <code>Perform a multi-step unit conversion pipeline that begins with converting an angle from degrees to radians, then uses that result as part of a derived length calculation. Specifically: (1) Convert 90 degrees to radians. (2) Use the resulting radian value as the angular displacement in a circular arc formula (arc length = radius × angle in radians) assuming a radius of 5 meters, yielding an arc length in meters. (3) Convert that arc length from meters to inches. (4) Separately, convert a mass of 2.5 kilograms to pounds. (5) Convert a temperature of 100 degrees Celsius to Fahrenheit. (6) Convert a volume of 3.785 liters (equivalent to 1 US gallon) to cubic inches. (7) Convert a data size of 8192 megabytes to gigabytes. (8) Convert a time duration of 90 minutes to seconds. Finally, package all eight results into a single structured JSON object with clearly labeled keys corresponding to each step.</code> | <code>Find up to 5 academic conferences in the next 3 months that have issued a call for papers related to 'large language models' and 'agent systems'. Return a structured list containing each conference's name, deadline (if available in the tool response), and a brief description.</code>                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                        | <code>0.0</code> |
* Loss: [<code>CosineSimilarityLoss</code>](https://sbert.net/docs/package_reference/sentence_transformer/losses.html#cosinesimilarityloss) with these parameters:
  ```json
  {
      "loss_fct": "torch.nn.modules.loss.MSELoss"
  }
  ```

### Training Hyperparameters
#### Non-Default Hyperparameters

- `per_device_train_batch_size`: 16
- `per_device_eval_batch_size`: 16
- `num_train_epochs`: 2
- `multi_dataset_batch_sampler`: round_robin

#### All Hyperparameters
<details><summary>Click to expand</summary>

- `overwrite_output_dir`: False
- `do_predict`: False
- `eval_strategy`: no
- `prediction_loss_only`: True
- `per_device_train_batch_size`: 16
- `per_device_eval_batch_size`: 16
- `per_gpu_train_batch_size`: None
- `per_gpu_eval_batch_size`: None
- `gradient_accumulation_steps`: 1
- `eval_accumulation_steps`: None
- `torch_empty_cache_steps`: None
- `learning_rate`: 5e-05
- `weight_decay`: 0.0
- `adam_beta1`: 0.9
- `adam_beta2`: 0.999
- `adam_epsilon`: 1e-08
- `max_grad_norm`: 1
- `num_train_epochs`: 2
- `max_steps`: -1
- `lr_scheduler_type`: linear
- `lr_scheduler_kwargs`: None
- `warmup_ratio`: 0.0
- `warmup_steps`: 0
- `log_level`: passive
- `log_level_replica`: warning
- `log_on_each_node`: True
- `logging_nan_inf_filter`: True
- `save_safetensors`: True
- `save_on_each_node`: False
- `save_only_model`: False
- `restore_callback_states_from_checkpoint`: False
- `no_cuda`: False
- `use_cpu`: False
- `use_mps_device`: False
- `seed`: 42
- `data_seed`: None
- `jit_mode_eval`: False
- `bf16`: False
- `fp16`: False
- `fp16_opt_level`: O1
- `half_precision_backend`: auto
- `bf16_full_eval`: False
- `fp16_full_eval`: False
- `tf32`: None
- `local_rank`: 0
- `ddp_backend`: None
- `tpu_num_cores`: None
- `tpu_metrics_debug`: False
- `debug`: []
- `dataloader_drop_last`: False
- `dataloader_num_workers`: 0
- `dataloader_prefetch_factor`: None
- `past_index`: -1
- `disable_tqdm`: False
- `remove_unused_columns`: True
- `label_names`: None
- `load_best_model_at_end`: False
- `ignore_data_skip`: False
- `fsdp`: []
- `fsdp_min_num_params`: 0
- `fsdp_config`: {'min_num_params': 0, 'xla': False, 'xla_fsdp_v2': False, 'xla_fsdp_grad_ckpt': False}
- `fsdp_transformer_layer_cls_to_wrap`: None
- `accelerator_config`: {'split_batches': False, 'dispatch_batches': None, 'even_batches': True, 'use_seedable_sampler': True, 'non_blocking': False, 'gradient_accumulation_kwargs': None}
- `parallelism_config`: None
- `deepspeed`: None
- `label_smoothing_factor`: 0.0
- `optim`: adamw_torch_fused
- `optim_args`: None
- `adafactor`: False
- `group_by_length`: False
- `length_column_name`: length
- `project`: huggingface
- `trackio_space_id`: trackio
- `ddp_find_unused_parameters`: None
- `ddp_bucket_cap_mb`: None
- `ddp_broadcast_buffers`: False
- `dataloader_pin_memory`: True
- `dataloader_persistent_workers`: False
- `skip_memory_metrics`: True
- `use_legacy_prediction_loop`: False
- `push_to_hub`: False
- `resume_from_checkpoint`: None
- `hub_model_id`: None
- `hub_strategy`: every_save
- `hub_private_repo`: None
- `hub_always_push`: False
- `hub_revision`: None
- `gradient_checkpointing`: False
- `gradient_checkpointing_kwargs`: None
- `include_inputs_for_metrics`: False
- `include_for_metrics`: []
- `eval_do_concat_batches`: True
- `fp16_backend`: auto
- `push_to_hub_model_id`: None
- `push_to_hub_organization`: None
- `mp_parameters`: 
- `auto_find_batch_size`: False
- `full_determinism`: False
- `torchdynamo`: None
- `ray_scope`: last
- `ddp_timeout`: 1800
- `torch_compile`: False
- `torch_compile_backend`: None
- `torch_compile_mode`: None
- `include_tokens_per_second`: False
- `include_num_input_tokens_seen`: no
- `neftune_noise_alpha`: None
- `optim_target_modules`: None
- `batch_eval_metrics`: False
- `eval_on_start`: False
- `use_liger_kernel`: False
- `liger_kernel_config`: None
- `eval_use_gather_object`: False
- `average_tokens_across_devices`: True
- `prompts`: None
- `batch_sampler`: batch_sampler
- `multi_dataset_batch_sampler`: round_robin

</details>

### Framework Versions
- Python: 3.12.3
- Sentence Transformers: 3.4.1
- Transformers: 4.57.6
- PyTorch: 2.11.0+cu130
- Accelerate: 1.13.0
- Datasets: 4.8.4
- Tokenizers: 0.22.2

## Citation

### BibTeX

#### Sentence Transformers
```bibtex
@inproceedings{reimers-2019-sentence-bert,
    title = "Sentence-BERT: Sentence Embeddings using Siamese BERT-Networks",
    author = "Reimers, Nils and Gurevych, Iryna",
    booktitle = "Proceedings of the 2019 Conference on Empirical Methods in Natural Language Processing",
    month = "11",
    year = "2019",
    publisher = "Association for Computational Linguistics",
    url = "https://arxiv.org/abs/1908.10084",
}
```

<!--
## Glossary

*Clearly define terms in order to be accessible across audiences.*
-->

<!--
## Model Card Authors

*Lists the people who create the model card, providing recognition and accountability for the detailed work that goes into its construction.*
-->

<!--
## Model Card Contact

*Provides a way for people who have updates to the Model Card, suggestions, or questions, to contact the Model Card authors.*
-->