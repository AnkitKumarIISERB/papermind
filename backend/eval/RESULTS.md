# Agent Evaluation Results

**Date**: auto-generated
**Model**: llama-3.3-70b-versatile
**Questions**: 17 (13 answerable, 4 unanswerable)

## Summary

| Metric | Agent | RAG (baseline) |
|--------|-------|----------------|
| Avg Citation Validity (answerable) | 0% | 0% |
| Avg Latency (seconds) | 0.0s | 0.0s |
| Unanswerable Decline Rate | 0% | N/A |
| Errors | 17/17 | 17/17 |

## Per-Question Results

| # | Question | Unanswerable | Agent Tools | Agent Cit Valid | Agent Declined | Agent Latency | RAG Latency |
|---|----------|:---:|:---:|:---:|:---:|:---:|:---:|
| 1 | What are the main approaches to multimodal fusion ... |  | 0 | 0% | — | 0s | 0s |
| 2 | Which papers propose attention-based methods? |  | 0 | 0% | — | 0s | 0s |
| 3 | What datasets are commonly used for depression det... |  | 0 | 0% | — | 0s | 0s |
| 4 | Compare text-only vs multimodal approaches for men... |  | 0 | 0% | — | 0s | 0s |
| 5 | What is the role of speech features in emotion det... |  | 0 | 0% | — | 0s | 0s |
| 6 | Which papers achieve the highest F1 scores? |  | 0 | 0% | — | 0s | 0s |
| 7 | What transformer architectures are used in the ind... |  | 0 | 0% | — | 0s | 0s |
| 8 | What are the limitations of current multimodal met... |  | 0 | 0% | — | 0s | 0s |
| 9 | How is WavLM used in the indexed papers? |  | 0 | 0% | — | 0s | 0s |
| 10 | What evaluation protocols are used across the pape... |  | 0 | 0% | — | 0s | 0s |
| 11 | Which papers use DAIC-WOZ dataset? |  | 0 | 0% | — | 0s | 0s |
| 12 | What are the key findings about cross-dataset gene... |  | 0 | 0% | — | 0s | 0s |
| 13 | Summarize the methods used for audio feature extra... |  | 0 | 0% | — | 0s | 0s |
| 14 | What is the best recipe for chocolate cake? | ✓ | 0 | 0% | ✗ | 0s | 0s |
| 15 | What is the current stock price of Apple Inc? | ✓ | 0 | 0% | ✗ | 0s | 0s |
| 16 | Explain quantum teleportation and its applications... | ✓ | 0 | 0% | ✗ | 0s | 0s |
| 17 | What did the paper by Zuckerberg et al. 2025 on so... | ✓ | 0 | 0% | ✗ | 0s | 0s |

## Limitations

- **Small model tool-calling flakiness**: llama-3.1-8b-instant often fails at structured tool calls; llama-3.3-70b-versatile is more reliable but slower.
- **5-step iteration cap**: Complex multi-hop questions may be truncated.
- **Abstracts only**: The agent searches over paper abstracts, not full text.
- **Synthetic grounding**: Citation validity measures whether cited paper IDs exist in the DB, not whether the claim accurately reflects the paper content.
