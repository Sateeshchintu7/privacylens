# PrivacyLens

**An AI-Powered Privacy Policy Analysis Tool**

---

**Author:** Sateesh Kumar Payyavula  
**Supervisor:** Dr Jiankang Zhang  
**Programme:** MSc Cyber Security and Human Factors  
**Institution:** Bournemouth University  
**Academic Year:** 2025-2026

---

## Live Application

- **Web app:** https://privacylens-5yhe.vercel.app
- **GitHub repository:** https://github.com/Sateeshchintu7/privacylens

## Overview

PrivacyLens is a web-based tool that uses Large Language Models and Natural Language Processing to analyse privacy policies and present results in plain English. The tool addresses the readability gap between privacy policies written at university level (Flesch-Kincaid Grade 14+) and the comprehension level of average adult users (Grade 8-9).

The tool processes any privacy policy via URL, PDF upload, or pasted text and produces six output modes: plain-English clause cards, multilingual audio narration, four data visualisations, an interactive RAG chatbot, age-adaptive rewriting for children, and a comprehensive single-shot Gemini analysis report.

## Key Contributions

1. **First tool to cover GDPR + CCPA + DPDP India + EU AI Act Article 50 simultaneously** — no existing commercial or research tool covers all four.
2. **Age-adaptive Kids Mode** for children aged 8 to 17 with SAFE / ASK PARENT / BE CAREFUL verdicts.
3. **LLM-PP2025 34-category taxonomy** based on Xie et al. (USENIX Security 2025), superseding OPP-115's 12 categories.
4. **DarkBench dark pattern detection** based on Nestaas et al. (ICLR 2025).
5. **27-language audio output** with Gemini-based translation.
6. **Free to use** — commercial equivalents (OneTrust, TrustArc) cost thousands per month.

## Technology Stack

| Layer | Technology |
|---|---|
| Frontend | React 18, TypeScript, Vite 6, TailwindCSS |
| Backend | FastAPI (Python 3.11) |
| AI / NLP | Google Gemini 2.5 Pro |
| Vector Search | FAISS, Sentence-Transformers |
| Audio | gTTS (27 languages) |
| Readability | Textstat (Flesch-Kincaid) |
| Frontend Hosting | Vercel |
| Backend Hosting | AWS EC2 (m7i, Ubuntu 24.04) |

## Repository Structure

```
Privacy_Project_Final/
├── api/                        FastAPI backend routes
│   ├── main.py                 Application entry point
│   ├── prompt_loader.py        Prompt loading with fallback
│   └── routes/
│       ├── analyse.py          Main analysis endpoint (background jobs)
│       ├── analyse_report.py   Single-shot Gemini report
│       ├── ask.py              RAG chatbot endpoint
│       ├── audio.py            Text-to-speech with translation
│       ├── kids.py             Age-adaptive Kids Mode
│       └── translate.py        Batch translation endpoint
│
├── nlp/                        NLP pipeline modules
│   ├── clause_extractor.py     34-category zero-shot extraction
│   ├── compliance_mapper.py    GDPR/CCPA/DPDP/EU AI Act mapping
│   ├── dark_pattern_detector.py DarkBench 6-category detection
│   ├── llm_client.py           Gemini client with fallback
│   ├── mad_engine.py           Multi-dimensional risk scoring
│   ├── plain_rewriter.py       Plain English rewriter
│   └── readability.py          Flesch-Kincaid scoring
│
├── audio/                      Audio generation
│   └── tts_engine.py           gTTS with Unicode preservation
│
├── ingestion/                  Document ingestion
│   ├── scraper.py              URL scraper with SPA support
│   └── text_cleaner.py         Text cleaning utilities
│
├── prompts/                    Gemini prompt templates
│   ├── master_analysis.txt     34-field comprehensive analysis
│   └── clause_extraction.txt   Zero-shot clause extraction
│
├── evaluation/                 User study materials
│   └── user_study_utils.py     SUS questionnaire utilities
│
├── frontend/                   React frontend
│   ├── src/
│   │   ├── pages/              Landing, Analyse pages
│   │   ├── components/
│   │   │   ├── analysis/       Summary card, document input
│   │   │   ├── charts/         GDPR radar, risk heatmap, data flow
│   │   │   ├── layout/         Navbar, footer
│   │   │   └── modes/          Read, Listen, See, Ask, Kids, Report
│   │   ├── hooks/              useAnalysis, useTranslation
│   │   ├── api/                API client
│   │   └── constants/          Icons, risk colours
│   ├── vercel.json             Vercel proxy config (HTTPS to HTTP)
│   └── package.json            Frontend dependencies
│
├── requirements.txt            Python dependencies
└── README.md                   This file
```

## How to Run Locally

### Prerequisites

- Python 3.11 or higher
- Node.js 18 or higher
- A Google Gemini API key (free tier at https://aistudio.google.com)

### Backend Setup

```bash
# Clone or extract the source code
cd Privacy_Project_Final

# Create virtual environment
python -m venv venv

# Activate (Windows)
venv\Scripts\activate

# Activate (macOS or Linux)
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Create .env file with your API key
echo "GEMINI_API_KEY=your_key_here" > .env

# Start backend
uvicorn api.main:app --reload
```

Backend runs on http://localhost:8000

### Frontend Setup

```bash
cd frontend
npm install

# For local development, point to local backend
# Edit src/api/client.ts to use http://localhost:8000

npm run dev
```

Frontend runs on http://localhost:5173

## API Endpoints

| Method | Endpoint | Purpose |
|---|---|---|
| GET | /health | Service health check |
| POST | /api/analyse | Start full analysis (returns job_id) |
| GET | /api/analyse/status/{job_id} | Poll analysis status |
| POST | /api/analyse/report | Single-shot Gemini report |
| POST | /api/ask | RAG chatbot question answering |
| POST | /api/audio | Generate audio in target language |
| POST | /api/kids | Age-adaptive Kids Mode |
| POST | /api/translate | Batch translate strings |

## Key Results

| Metric | Result |
|---|---|
| Clause extraction Macro F1 | 0.85 |
| Google Policy readability | FK Grade 14.0 to Grade 3.5 |
| Microsoft Policy readability | FK Grade 14.2 to Grade 5.0 |
| OpenAI Policy readability | FK Grade 6.2 to Grade 3.9 |
| End-to-end analysis time | 32 seconds |
| Backend processing time | 7.9 seconds |
| Cache response time | Under 100 milliseconds |
| Regulations covered | GDPR + CCPA + DPDP + EU AI Act Art.50 |
| Languages supported | 27 languages for audio |

## Academic References

Key references underpinning this work:

- Xie, R. et al. (2025). A Large-Scale Empirical Measurement Study of Privacy Policies Using LLMs. USENIX Security 2025.
- Nestaas, S. et al. (2025). DarkBench: Benchmarking Dark Patterns in Large Language Models. ICLR 2025.
- Kincaid, J.P. et al. (1975). Derivation of new readability formulas. Naval Technical Training Command.
- Brooke, J. (1996). SUS: A quick and dirty usability scale.
- European Parliament and Council. (2024). Regulation EU 2024/1689 — Artificial Intelligence Act.
- Digital Personal Data Protection Act. (2023). Government of India.
- California Consumer Privacy Act. (2018). Civil Code Section 1798.100.

Full reference list in the accompanying dissertation document.

## License

Academic use only. This work is submitted in partial fulfilment of the MSc Cyber Security and Human Factors at Bournemouth University.

## Contact

For questions about this submission, contact the author through Bournemouth University.
