---
tags:
- sentence-transformers
- sentence-similarity
- feature-extraction
- generated_from_trainer
- dataset_size:1117
- loss:CosineSimilarityLoss
base_model: sentence-transformers/all-MiniLM-L6-v2
widget:
- source_sentence: 'Calculate the final adjusted score for a performance evaluation
    based on the following steps: Start with raw scores [88.3, 92.7, 76.5, 85.9, 90.1].
    First, compute their arithmetic mean. Then, subtract 5.2 from this mean. Multiply
    the result by 1.15 to apply a scaling factor. Round the scaled value to the nearest
    integer. Separately, find the minimum and maximum of the raw scores, add them
    together, and divide that sum by 2 to get the mid-range value. Finally, add the
    rounded scaled mean and the mid-range value to produce the final adjusted score.
    Return the final adjusted score as a single number in a JSON object with key ''final_adjusted_score''.'
  sentences:
  - 'A travel agency is planning a promotional campaign for destinations with stable
    and pleasant weather over the next 5 days. First, search for locations matching
    the query ''San Jose'' to disambiguate possible cities. From the results, select
    the city named ''San Jose'' in the United States. Then, retrieve the current weather
    for that city to assess immediate conditions. Finally, obtain a 5-day weather
    forecast for the same city. Based on the combined data, generate a structured
    report indicating whether the location qualifies as ''weather-stable''—defined
    as having no precipitation in the forecast and daily temperature variation (max
    - min) under 10°C for all 5 days. Return the result as a JSON object with keys:
    ''city'', ''current_weather_summary'', ''forecast_stable'', and ''recommendation''.'
  - 'Can you calculate the average daily temperature over the past 7 days using these
    recorded values in Celsius: 23.6, 25.1, 22.9, 24.0, 26.3, 21.8, and 25.7? Please
    find the exact mean by summing them up and dividing by 7, then round it to the
    nearest whole number using standard rounding rules. I’d like the final result
    as an integer in a JSON object with the key "rounded_average".'
  - Identify the top liquidity pool by 24-hour trading volume on the Ethereum network,
    then retrieve its full details, historical OHLCV data for the past 7 days at 1-hour
    intervals, and the 10 most recent transactions. Additionally, use the search tool
    to confirm the primary token in that pool exists across other networks, and summarize
    all findings in a structured report.
- source_sentence: Hey, I’ve been working on a machine learning project with a teammate,
    and we’ve been using a notebook called `model_training.ipynb` in the `experiments/q3_eval/`
    folder. I’m pretty sure the evaluation part hasn’t been updated recently—it’s
    probably still just reporting accuracy—but I want to double-check and improve
    it. Can you look in that directory and see if there are any other notebooks modified
    in the last week that might have newer evaluation code? If not, go ahead and open
    `model_training.ipynb`. The evaluation logic should be somewhere around cells
    12 to 15—just skim through to find it. If it’s only using `accuracy_score`, please
    update it to also compute and print the F1-score and AUC (using `sklearn.metrics`).
    Add a short markdown cell right above explaining that we’re expanding the metrics
    beyond accuracy for better model assessment. After making the change, run that
    updated code block and show me the actual output it produces. Oh, and once you're
    done, could you list all currently running notebook sessions? I just want to make
    sure we didn’t accidentally spin up any extra kernels while doing this. Please
    make sure the final answer is backed by specific data, concrete numbers, or verifiable
    sources.
  sentences:
  - 'Hey, I''m trying to figure out if we can use the official X (Twitter) API for
    our social listening dashboard—specifically to post tweets programmatically. Before
    diving into code, I need to confirm a few technical details from the actual API
    docs. Can you help me find: - The base URL for the X API, - Whether OAuth 2.0
    is strictly required (or if there’s another auth method), - Exactly what the request
    body should look like when creating a tweet (e.g., is it JSON? what fields are
    needed?), and - Any specific rate limits tied to that tweet-creation endpoint?
    I’d really appreciate it if you could pull this info straight from the official
    spec—especially the exact scopes needed and hard numbers on rate limits, not just
    general guidance.'
  - Find the highest-rated coffee shop that is currently open within 1.5 km of the
    Empire State Building in New York City. Retrieve its full details including address,
    phone number, and operating hours. Then, calculate the walking distance and duration
    from the Empire State Building to this coffee shop. Finally, determine the elevation
    at both the Empire State Building and the coffee shop’s location.
  - 'Hey, I''m trying to figure out if we can use the official X (Twitter) API for
    our social listening dashboard—specifically to post tweets programmatically. Before
    diving into code, I need to confirm a few technical details from the actual API
    docs. Can you help me find: - The base URL for the X API, - Whether OAuth 2.0
    is strictly required (or if there’s another auth method), - Exactly what the request
    body should look like when creating a tweet (e.g., is it JSON? what fields are
    needed?), and - Any specific rate limits tied to that tweet-creation endpoint?
    I’d really appreciate it if you could pull this info straight from the official
    spec—especially the exact scopes needed and hard numbers on rate limits, not just
    general guidance.'
- source_sentence: Hey, can you help me figure out why the promo code 'SAVE10' sometimes
    breaks checkout on our test site? I’ve been seeing weird intermittent issues.
    Could you go to https://shop.example.test, add any product to the cart, head to
    checkout, and try applying that code? If a browser popup shows up—like an alert
    or prompt—just click OK. Once the discount confirmation appears, grab a screenshot
    of the whole order summary and save it as 'final_checkout.png'. Also, I need the
    exact final total price (pull it directly from the page with JS if possible) and
    a list of all network requests that fired while applying the promo—especially
    any that failed. Just close the tab when you’re done. Thanks! Please make sure
    the final answer is backed by specific data, concrete numbers, or verifiable sources.
  sentences:
  - 'Perform a multi-step unit conversion pipeline that begins with converting an
    angle from degrees to radians, then uses that result as part of a derived length
    calculation. Specifically: (1) Convert 90 degrees to radians. (2) Use the resulting
    radian value as the angular displacement in a circular arc formula (arc length
    = radius × angle in radians) assuming a radius of 5 meters, yielding an arc length
    in meters. (3) Convert that arc length from meters to inches. (4) Separately,
    convert a mass of 2.5 kilograms to pounds. (5) Convert a temperature of 100 degrees
    Celsius to Fahrenheit. (6) Convert a volume of 3.785 liters (equivalent to 1 US
    gallon) to cubic inches. (7) Convert a data size of 8192 megabytes to gigabytes.
    (8) Convert a time duration of 90 minutes to seconds. Finally, package all eight
    results into a single structured JSON object with clearly labeled keys corresponding
    to each step.'
  - Can you look up the 2023 European heatwaves on Wikipedia and tell me what caused
    them, especially how climate change played a role? I’d like a short summary (no
    more than 150 words) of the main causes from the article, along with up to five
    specific facts from the same source that directly link the event to climate change.
    Also, please list up to eight related topics from the article that connect to
    extreme weather or climate science. Make sure everything comes only from Wikipedia
    and include the exact title of the article you used.
  - Identify a well-known painting titled 'The Harvesters' in the Metropolitan Museum
    of Art, retrieve its full details including image, and confirm it belongs to the
    European Paintings department. Begin by listing all museum departments to obtain
    the correct department ID, then search for the object by title within that department,
    and finally fetch the complete object record with image.
- source_sentence: 'I''m investigating a sudden price swing in the WBTC/ETH liquidity
    pool on Ethereum that occurred over the past 7 days. First, confirm which networks
    are supported, then identify the top DEXes on Ethereum. Locate the WBTC/ETH pool
    with the highest 24-hour trading volume, retrieve its detailed metrics, and pull
    hourly OHLCV data for the last 7 days to analyze volatility patterns. Finally,
    get the 10 most recent swap transactions in that pool to see if any large trades
    correlate with price movements. Deliver a summary including: (1) pool address,
    (2) total volume over the period, (3) max single-hour price change, and (4) count
    of transactions exceeding $500k in value.'
  sentences:
  - 'I’m preparing for an elective abdominal aortic aneurysm repair on a 68-year-old
    male patient and need a comprehensive preoperative risk assessment. He weighs
    82 kg, is 70 inches tall, has type 2 diabetes managed with insulin, and known
    coronary artery disease treated medically—no prior heart failure or stroke. His
    serum creatinine is 1.4 mg/dL, blood pressure was last recorded at 152/88 mmHg,
    total cholesterol is 210 mg/dL, HDL is 42 mg/dL, and he’s a current smoker. He’s
    on antihypertensives but not on a statin. Could you please calculate his Revised
    Cardiac Risk Index score and tell me what risk category that puts him in? Also,
    using his creatinine, age, sex, and the 2021 CKD-EPI creatinine equation (not
    the one with cystatin C), determine his eGFR. With that eGFR plus his age, sex,
    lipid levels, smoking status, diabetes, and antihypertensive use, estimate his
    10-year cardiovascular disease risk using the PREVENT model. Lastly, figure out
    his ideal body weight and adjusted body weight for dosing purposes. I’d appreciate
    it if you could pull all this together into a clear summary with the actual numbers:
    RCRI score and category, eGFR value, 10-year CVD risk percentage, and both ideal
    and adjusted weights in kilograms.'
  - 'A 68-year-old male patient presents for preoperative evaluation prior to elective
    abdominal aortic aneurysm repair. His serum creatinine is 1.4 mg/dL, weight is
    82 kg, height is 70 inches, and he has type 2 diabetes treated with insulin. He
    reports no history of heart failure or stroke but has known coronary artery disease
    managed medically. His last menstrual period is irrelevant (he’s male), but his
    last blood pressure reading was 152/88 mmHg, total cholesterol is 210 mg/dL, HDL
    is 42 mg/dL, and he is a current smoker. He is not on statins but is taking antihypertensives.
    Calculate his Revised Cardiac Risk Index score first. Then, use his creatinine
    to compute eGFR via the 2021 CKD-EPI creatinine equation (not cystatin C). With
    that eGFR, age, sex, lipid profile, smoking status, diabetes status, and antihypertensive
    use, calculate his 10-year cardiovascular disease risk using the PREVENT model.
    Finally, determine his ideal and adjusted body weight for dosing considerations.
    Return a structured preoperative risk summary containing: (1) RCRI score and risk
    category, (2) eGFR value, (3) 10-year CVD risk percentage, and (4) ideal and adjusted
    body weights in kilograms.'
  - 'I''m evaluating whether to integrate the official X (Twitter) API into our social
    listening dashboard. Before writing any code, I need a clear understanding of
    its authentication requirements and rate limits. Start by retrieving an overview
    of the X API specification using its known identifier. Then, examine the details
    of the ''create_tweet'' operation to determine what OAuth scopes are required
    and whether it supports JSON payloads. Finally, produce a concise technical summary
    that includes: (1) the base URL of the API, (2) whether OAuth 2.0 is mandatory,
    (3) the exact request payload format for creating a tweet, and (4) any documented
    rate limits for that endpoint.'
- source_sentence: 'Perform a health check on the OKX Exchange server, then retrieve
    the latest price for BTC-USDT. Using that instrument, fetch the last 96 candlesticks
    at a 1-hour interval (covering the past 4 days). Based on this data, compute the
    average closing price over the period and determine whether the latest price is
    above or below this average. Return a JSON object containing: {"health_status":
    "ok" or error message, "latest_price": number, "average_close_price": number,
    "price_vs_average": "above" or "below"}.'
  sentences:
  - 'I need to set up a data analysis notebook in my project folder. First, check
    the root directory and its immediate subfolders for any Jupyter notebooks. If
    you find one called ''analysis_pipeline.ipynb'', open it; if not, create a new
    one with that name at the top level. Once it’s ready, take a quick look at its
    contents—just the first 50 lines or so. If it’s empty or has fewer than three
    cells, add the following at the very beginning: 1. A markdown cell with the title
    “# Data Analysis Pipeline” 2. A code cell that prints “Pipeline initialized on
    [today’s date]” (formatted like YYYY-MM-DD) 3. A code cell that runs `%lsmagic`
    to show available kernels Then run the second and third cells one after the other,
    giving each up to 60 seconds to finish. After they’ve run, restart the kernel
    to clear everything out. When you’re done, please give me a summary that includes:
    - The full file path of the notebook - How many cells it has now - The exact output
    from the `%lsmagic` command - Confirmation that the kernel was successfully restarted'
  - 'I’m trying to decide whether I should accept a new job offer in the next three
    months. I’d like some guidance using two specific approaches: first, a bibliomantic
    reading done exactly as Philip K. Dick practiced it, applied to this question;
    and second, an I Ching divination that gives me a hexagram for the same question.
    From the I Ching result, I need the actual hexagram number (like 1 through 64),
    its traditional name, and the full classical interpretation of that hexagram.
    Please put together a clear comparison that includes: (1) the insight from the
    bibliomancy, (2) the hexagram number and name, and (3) the complete traditional
    meaning of that hexagram—so I can thoughtfully weigh both perspectives.'
  - 'Can you check the current status of the OKX exchange, get the latest BTC-USDT
    price, and then pull the last 96 one-hour candlesticks (covering the past 4 days)?
    From that data, I’d like to know the highest and lowest prices during this period,
    along with a clear summary that includes: the current BTC-USDT price, the 4-day
    high, the 4-day low, and whether the current price is within 5% of that 4-day
    high. Please provide the actual numbers so I can verify the calculation.'
pipeline_tag: sentence-similarity
library_name: sentence-transformers
---

# SentenceTransformer based on sentence-transformers/all-MiniLM-L6-v2

This is a [sentence-transformers](https://www.SBERT.net) model finetuned from [sentence-transformers/all-MiniLM-L6-v2](https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2). It maps sentences & paragraphs to a 384-dimensional dense vector space and can be used for semantic textual similarity, semantic search, paraphrase mining, text classification, clustering, and more.

## Model Details

### Model Description
- **Model Type:** Sentence Transformer
- **Base model:** [sentence-transformers/all-MiniLM-L6-v2](https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2) <!-- at revision 1110a243fdf4706b3f48f1d95db1a4f5529b4d41 -->
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
    'Perform a health check on the OKX Exchange server, then retrieve the latest price for BTC-USDT. Using that instrument, fetch the last 96 candlesticks at a 1-hour interval (covering the past 4 days). Based on this data, compute the average closing price over the period and determine whether the latest price is above or below this average. Return a JSON object containing: {"health_status": "ok" or error message, "latest_price": number, "average_close_price": number, "price_vs_average": "above" or "below"}.',
    'Can you check the current status of the OKX exchange, get the latest BTC-USDT price, and then pull the last 96 one-hour candlesticks (covering the past 4 days)? From that data, I’d like to know the highest and lowest prices during this period, along with a clear summary that includes: the current BTC-USDT price, the 4-day high, the 4-day low, and whether the current price is within 5% of that 4-day high. Please provide the actual numbers so I can verify the calculation.',
    "I need to set up a data analysis notebook in my project folder. First, check the root directory and its immediate subfolders for any Jupyter notebooks. If you find one called 'analysis_pipeline.ipynb', open it; if not, create a new one with that name at the top level. Once it’s ready, take a quick look at its contents—just the first 50 lines or so. If it’s empty or has fewer than three cells, add the following at the very beginning: 1. A markdown cell with the title “# Data Analysis Pipeline” 2. A code cell that prints “Pipeline initialized on [today’s date]” (formatted like YYYY-MM-DD) 3. A code cell that runs `%lsmagic` to show available kernels Then run the second and third cells one after the other, giving each up to 60 seconds to finish. After they’ve run, restart the kernel to clear everything out. When you’re done, please give me a summary that includes: - The full file path of the notebook - How many cells it has now - The exact output from the `%lsmagic` command - Confirmation that the kernel was successfully restarted",
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

* Size: 1,117 training samples
* Columns: <code>sentence_0</code>, <code>sentence_1</code>, and <code>label</code>
* Approximate statistics based on the first 1000 samples:
  |         | sentence_0                                                                           | sentence_1                                                                          | label                                                          |
  |:--------|:-------------------------------------------------------------------------------------|:------------------------------------------------------------------------------------|:---------------------------------------------------------------|
  | type    | string                                                                               | string                                                                              | float                                                          |
  | details | <ul><li>min: 46 tokens</li><li>mean: 161.25 tokens</li><li>max: 256 tokens</li></ul> | <ul><li>min: 46 tokens</li><li>mean: 162.4 tokens</li><li>max: 256 tokens</li></ul> | <ul><li>min: 0.0</li><li>mean: 0.32</li><li>max: 1.0</li></ul> |
* Samples:
  | sentence_0                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                               | sentence_1                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                  | label            |
  |:---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|:--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|:-----------------|
  | <code>Can you put together a detailed space weather and planetary observation report covering the last 7 days? I need it to include all significant solar activity—specifically coronal mass ejections (CMEs), solar flares (FLRs), and geomagnetic storms (GSTs)—with their exact dates and full event details. For each of those events, please include the corresponding scientific data tied to their occurrence dates. Also, add the WSA+Enlil model forecast summary for that same week to show how predictions aligned with actual conditions. On the astronomy side, I’d like NASA’s Picture of the Day for each of the past 7 days (from 7 days ago through yesterday), including the image metadata and captions. And as a planetary highlight, please include the very latest photo taken by the Curiosity rover on Mars, along with the sol number and camera information. Put everything into one organized JSON file with clear sections: space weather events with types, dates, and data; the 7 astronomy images; the newest C...</code> | <code>I'm planning a Pacific Northwest trip through California, Oregon, and Washington and want to visit national parks where I can both hike and camp. Can you give me a detailed report on all such parks in those three states? For each park, please include: the park name and a brief description; any current alerts that mention the word “closure”; the names and operating hours of all open visitor centers; the names of available campgrounds along with their amenities (like restrooms, potable water, etc.); and a list of upcoming events scheduled in the next 30 days, including event titles and dates. I’d like everything compiled clearly so I can compare options and plan accordingly. Please make sure the final answer is backed by specific data, concrete numbers, or verifiable sources.</code>                                                                                                               | <code>0.0</code> |
  | <code>A research team is investigating recent advances in federated learning applied to healthcare diagnostics. They need a consolidated report of relevant preprints and peer-reviewed literature from the past 30 days across multiple repositories. First, search bioRxiv and medRxiv for 'federated learning' to capture health-focused preprints. Then, use those results to refine a broader query for PubMed (to find peer-reviewed clinical studies) and arXiv (for foundational algorithmic work). Finally, run a Semantic Scholar search with the same core query but filtered to the last month to cross-validate coverage and identify highly cited emerging papers. Deliver a structured JSON list of up to 15 unique papers, each with source repository, title, publication/preprint date, and a one-sentence summary of its contribution to healthcare-oriented federated learning.</code>                                                                                                                                               | <code>I need help with a multi-part unit conversion and calculation task. First, convert 98.6°F to Kelvin. Then, using that temperature as the final value (assuming the initial temperature is 0°C), calculate the thermal energy required to heat 2 kg of water, given water’s specific heat capacity is 1 calorie/(gram·°C). For this, convert the water mass to grams and treat the temperature difference in Celsius (remembering that a change of 1 K equals a change of 1°C). Next, convert the resulting energy from kilocalories to joules. Separately, convert 60 miles per hour to meters per second, and also convert 5 acres to square meters. Please provide all intermediate and final values in a clear summary with these exact labels: body_temperature_K, water_mass_g, delta_T_C, thermal_energy_kcal, thermal_energy_J, speed_m_s, and area_sq_m. I’d like to see the actual numbers so I can verify each step.</code> | <code>0.0</code> |
  | <code>I'm working on a cross-platform dashboard app and need to pick the right icons for four main navigation items: 'dashboard', 'user profile', 'notifications', and 'settings'. Can you check what’s available in the Hugeicons library, tell me how many total icons there are, and find the best matches for those four features? Then, please provide clear, ready-to-use implementation instructions for React, Vue, and Flutter so each frontend team can drop them in right away. I’d like all this info in a single JSON object with the total icon count, the matched icons per feature, and the platform-specific usage guidance.</code>                                                                                                                                                                                                                                                                                                                                                                                                     | <code>Perform a comprehensive health and data validation workflow for the Game Trends server, then generate a unified gaming trends report covering both Steam and Epic Games platforms. First, execute a local health check to confirm basic server functionality. Next, verify the external API health status. Only if both health checks pass, proceed to gather: (1) Steam's current top sellers, (2) Steam's most played games, (3) Steam's trending games, (4) Epic's current and upcoming free games (valid for the next 3 months), and (5) Epic's trending games. Finally, cross-validate these results by invoking the all-platforms trending data endpoint and compile a structured report listing the top 5 overlapping titles between Steam and Epic trending lists, along with sales rank, player count (if available), and free promotion status.</code>                                                                      | <code>0.0</code> |
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