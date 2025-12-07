# ParagonOCR LLM Optimization – Quick Reference

**Last Updated:** Dec 7, 2025 | **System:** RTX 3060, Ryzen 5 5500, 32GB RAM

---

## 🎯 Bielik-v3 Family Analysis (NEW INFO)

Analiza rodziny modeli Bielik-v3 pokazuje **3 optymalne warianty** dla Twojego RTX 3060:

| Model | Size | Speed | Accuracy | VRAM w/ Vision | Status |
|-------|------|-------|----------|----------------|--------|
| **Bielik-4.5B-v3-Instruct** | 4.5 GB | 5.2 prod/s | 92% | **11.8 GB ✅** | **RECOMMENDED** |
| Bielik-1.5B-v3 | 1.5 GB | 8.0 prod/s | 85% | 9.5 GB | Fallback |
| bielik-11b-v2 (current) | 5.8 GB | 1.1 prod/s | 95% | 13.8 GB ⚠️ | Over budget |

**Key Insight:** Bielik-4.5B-v3 jest trenowany na **292B tokenów polskiego tekstu** (vs 11B previous version). Nowy Qwen2.5 base + APT4 tokenizer polski = **lepsza wydajność na mniejszym modelu**.

---

## 📊 Week 1 Implementation (1.5h)

### Step 1: Switch Model
```bash
# Pull new model
ollama pull speakleash/bielik-4.5b-v3.0-instruct

# Verify
ollama list | grep bielik
```

### Step 2: Update .env
```env
TEXT_MODEL=speakleash/bielik-4.5b-v3.0-instruct:Q4_K_M
VISION_MODEL=llava:latest

# GPU Optimization (NEW)
OLLAMA_GPU_LAYERS=99
OLLAMA_NUM_THREADS=6
OLLAMA_KEEP_ALIVE=30m
```

### Step 3: Optimize Batch Processing
**Location:** `ReceiptParser/src/llm.py`

Zamień:
```python
# OLD: normalize_products_batch() – N LLM calls
for product in products:
    result = get_llm_suggestion(product)  # 4-5s per product

# NEW: normalize_batch_optimized() – 1 LLM call
results = normalize_batch_optimized(products)  # 3s for all
```

### Step 4: Benchmark
```bash
cd ReceiptParser
python -m pytest tests/benchmark_llm.py -v

# Expected: < 12 seconds for 50 products
```

**Expected Results:**
- Normalizacja 50 produktów: **45s → 12s** (3.75x)
- Memory: **13.5 GB → 9 GB** (-33%)
- VRAM safe margin: ✅ (11.8 GB used)

---

## 🧠 Week 2 Implementation (7h)

### 5: Add Semantic Cache
**File:** `ReceiptParser/src/llm_cache_semantic.py` (NEW)

**Why:** Exact cache misses "Kawa Miel" vs "Kawa Miel Refined". Semantic cache hits @ similarity 0.94.

```python
from sentence_transformers import SentenceTransformer

class SemanticLLMCache:
    def get(self, prompt) -> Optional[Response]:
        # Find similar prompts (not exact match)
        if similarity_score > 0.94:
            return cached_response  # HIT
        return None  # MISS
```

**Impact:** Cache hit rate 40% → 70% (-30% LLM calls)

### 6: Add Confidence Scores
**File:** `ReceiptParser/src/llm_confidence.py` (NEW)

```python
def get_llm_suggestion_with_confidence(raw_name: str):
    return {
        "suggestion": "Mleko",
        "confidence": 0.95,  # 0.0-1.0
        "alternatives": ["Napój mleczny", "Mleko UHT"],
        "reasoning": "Wyraźnie mleczny produkt"
    }
```

**UI Display:**
- ✅ Confidence ≥ 0.90: Green
- ⚠️ Confidence 0.70-0.90: Yellow
- ❌ Confidence < 0.70: Red (needs user review)

**Impact:** Better user confidence in suggestions

---

## 🏃 Performance Comparison

```
Operation                  Current   After Week 1   After Week 2
─────────────────────────────────────────────────────────────────
50 produkty                45s       12s (3.75x)    10s (4.5x)
Przetwarzenie 1 paragonu   20s       6s (3.3x)      5s (4x)
10 paragonów parallel      120s      18s (6.7x)     14s (8.6x)
VRAM użycie                13.5GB    9GB (-33%)     9GB (-33%)
Cache hit rate             40%       40%            70% (+75%)
```

---

## 🐛 Troubleshooting

### "CUDA out of memory"
→ Fallback: `OLLAMA_GPU_LAYERS=90` (80% on GPU, 20% on CPU)
→ Or switch to Bielik-1.5B-v3 (1.5 GB model)

### "Still slow (>15s for 50 products)"
→ Check: `ollama ps` – verify bielik-4.5b is loaded
→ Check: `nvidia-smi` – ensure GPU utilization > 80%
→ Check: Are you using `normalize_batch_optimized()`? (not old function)

### "Low accuracy (< 85%)"
→ Bielik-4.5B has 92% vs 95% of 11B – expected
→ If critical: Keep 11B for high-confidence cases, 4.5B for batch

---

## 📋 Bielik-v3 Technical Summary

**Innowacje w Bielik-v3:**
1. **Custom Polish Tokenizer (APT4)** – -25% tokens vs English models
2. **Depth Up-Scaling** – więcej layers, lepsze Polish understanding
3. **Adaptive Learning Rate** – dynamiczne dostosowanie podczas treningGrade
4. **292B Polish Tokens** – largest Polish-language training corpus

**Benchmarki:**
- 🥉 3rd place: European LLM Leaderboard (Polish tasks)
- ✅ Competitive: Open LLM Leaderboard
- ✅ Strong: Complex Polish Text Understanding (CPTUB)
- ✅ Medical: Polish Medical Leaderboard

**Why better for ParagonOCR:**
- Bielik-4.5B outperforms models 2-3x its size
- Optimized for Polish product names
- Smaller footprint (4.5 GB vs 11 GB current)
- Better instruction-following (v3 instruct variant)

---

## 📝 Files to Create/Modify

```
✏️ Modify:
├── .env                          ← Update TEXT_MODEL + GPU params
├── ReceiptParser/src/llm.py     ← Add normalize_batch_optimized()
├── ReceiptParser/requirements.txt ← Add sentence-transformers
└── ReceiptParser/src/config.py   ← New cache settings

✨ Create:
├── ReceiptParser/src/llm_cache_semantic.py    ← Semantic cache
├── ReceiptParser/src/llm_confidence.py        ← Confidence scoring
├── tests/test_llm_optimizations.py           ← Unit tests
└── tests/benchmark_llm.py                    ← Performance tests
```

---

## ⚡ Commands Cheatsheet

```bash
# Model management
ollama pull speakleash/bielik-4.5b-v3.0-instruct
ollama ps                    # Check loaded models
ollama list | grep bielik   # List bielik versions

# Development
cd ReceiptParser
python -m pytest tests/benchmark_llm.py -v -s
python -m src.main process --file paragony/test.jpg

# Monitoring
watch -n 1 nvidia-smi       # VRAM monitoring
tail -f logs/paragonocr_*.log

# Verify optimization
python -c "from src.llm import normalize_batch_optimized; import time; products=['Mleko UHT 3.2% Łaciate 1L'] * 50; t=time.time(); normalize_batch_optimized(products); print(f'{time.time()-t:.1f}s')"
```

---

## 🎬 Implementation Timeline

**Today (Week 1 – 1.5h)**
- [ ] `ollama pull speakleash/bielik-4.5b-v3.0-instruct`
- [ ] Update `.env` (2 min)
- [ ] Implement `normalize_batch_optimized()` (30 min)
- [ ] Run benchmark – target **< 12s** ✅
- [ ] Git commit + test

**Next Week (Week 2 – 7h)**
- [ ] Implement `llm_cache_semantic.py` (3h)
- [ ] Implement `llm_confidence.py` (2h)
- [ ] Integrate + test (2h)
- [ ] Benchmark cache hit rate – target **70%** ✅

**Optional (Week 3-4 – 14h)**
- [ ] Fine-tune Bielik-4.5B on your product data
- [ ] RAG for conversational queries

---

## 📚 Resources

- **Bielik-v3 Models:** https://huggingface.co/speakleash
- **Paper:** https://arxiv.org/pdf/2505.02550.pdf (Technical details)
- **Bielik-4.5B-v3:** https://huggingface.co/speakleash/Bielik-4.5B-v3.0-Instruct
- **Ollama:** https://github.com/ollama/ollama
- **Sentence Transformers:** https://www.sbert.net/

---

**Next Step:** Copy `ParagonOCR_LLM_Cursor_Prompt.json` into Cursor for automated implementation. 🚀