# NyayAI — RAG Evaluation Report

Generated: 2026-11-15 15:43:45
Mode: full pipeline (retrieval + generation)

## Configuration

| Setting | Value |
| --- | --- |
| Embedding model | `BAAI/bge-m3` |
| LLM | `qwen2.5:3b` |
| Chunks in index | 3248 |
| Candidates fetched (fetch_k) | 15 |
| Chunks passed to LLM (top_k) | 5 |
| Abstention threshold | 0.52 cosine |
| Filter-fallback threshold | 0.55 cosine |

## Results

Cases: 33 (28 in scope, 5 out of scope). Errors: 0.

### 1. Routing (question -> legal domain)

- Vertical classification accuracy: **89.3%**

### 2. Retrieval

| Metric | Value |
| --- | --- |
| Source hit@5 (expected Act retrieved) | **100.0%** |
| Section hit@5 (expected section retrieved) | **65.2%** |
| Mean precision@5 | 92.1% |
| Mean reciprocal rank | 0.958 |
| Mean top similarity | 0.64 |

### 3. Abstention / hallucination guard

| Metric | Value |
| --- | --- |
| Correct refusals on out-of-scope questions | **80.0%** |
| False refusals on in-scope questions | 0.0% |
| Mean top similarity, in scope | 0.64 |
| Mean top similarity, out of scope | 0.459 |

### 4. Generation

| Metric | Value |
| --- | --- |
| Answers generated | 28 |
| Grounded (no invented section numbers) | **85.7%** |
| Unsupported section citations, total | **5** |
| Answers citing a section | 89.3% |
| Mean reference-keyword coverage | 91.3% |
| Answered in the language asked | 100.0% |
| Mean answer length | 1237 chars |

### Latency (seconds, M1 CPU, local models)

| Stage | Mean |
| --- | --- |
| Classify | 0.093 |
| Retrieve (embed + search) | 2.548 |
| Generate | 21.18 |

## Per-case results

| ID | Lang | Vertical | Src hit | Sec hit | Top sim | Grounded | Keywords | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| rti-01 | en | ok | yes | yes | 0.6128 | yes | 2/2 | ok |
| rti-02 | en | ok | yes | NO | 0.7161 | yes | 1/1 | ok |
| rti-03 | en | ok | yes | yes | 0.5896 | yes | 1/1 | ok |
| rti-04 | en | ok | yes | yes | 0.601 | yes | 1/1 | ok |
| rti-05 | mr | ok | yes | yes | 0.5946 | yes | - | ok |
| rti-06 | hi | ok | yes | NO | 0.6763 | yes | - | ok |
| ten-01 | en | ok | yes | yes | 0.6566 | yes | 1/1 | ok |
| ten-02 | en | ok | yes | NO | 0.7193 | yes | 1/1 | ok |
| ten-03 | en | ok | yes | - | 0.6581 | yes | 1/1 | ok |
| ten-04 | en | ok | yes | yes | 0.6751 | yes | 1/1 | ok |
| ten-05 | hi | ok | yes | yes | 0.5596 | yes | - | ok |
| con-01 | en | ok | yes | yes | 0.5677 | NO | 0/1 | invented sections: 82 |
| con-02 | en | ok | yes | NO | 0.673 | yes | 0/1 | missing: two years |
| con-03 | en | ok | yes | - | 0.6663 | yes | 1/1 | ok |
| con-04 | en | ok | yes | - | 0.6142 | NO | 1/1 | invented sections: 82 |
| con-05 | en | rti≠consumer | yes | yes | 0.7056 | yes | 1/1 | ok |
| fam-01 | en | ok | yes | yes | 0.6084 | yes | 1/1 | ok |
| fam-02 | en | ok | yes | NO | 0.7154 | NO | 1/1 | invented sections: 1, 13 |
| fam-03 | en | ok | yes | yes | 0.6191 | yes | 1/1 | ok |
| fam-04 | en | ok | yes | yes | 0.6192 | NO | 1/1 | invented sections: 12 |
| fam-05 | en | ok | yes | yes | 0.6082 | yes | 1/1 | ok |
| fam-06 | mr | rti≠family | yes | NO | 0.5455 | yes | - | ok |
| cri-01 | en | ok | yes | NO | 0.5588 | yes | 1/1 | ok |
| cri-02 | en | ok | yes | - | 0.7025 | yes | 1/1 | ok |
| cri-03 | en | ok | yes | - | 0.6854 | yes | 1/1 | ok |
| cri-04 | en | ok | yes | yes | 0.705 | yes | 1/1 | ok |
| cri-05 | en | ok | yes | yes | 0.7111 | yes | 1/1 | ok |
| cri-06 | hi | rti≠criminal | yes | NO | 0.5641 | yes | - | ok |
| oos-01 | en | out-of-scope | - | - | 0.4796 | - | - | refused |
| oos-02 | en | out-of-scope | - | - | 0.3847 | - | - | refused |
| oos-03 | en | out-of-scope | - | - | 0.4119 | - | - | refused |
| oos-04 | en | out-of-scope | - | - | 0.5588 | - | - | ANSWERED (should refuse) |
| oos-05 | en | out-of-scope | - | - | 0.4606 | - | - | refused |

Full per-case detail, including every retrieved chunk, is in `evaluation/results/eval_results.json`.
