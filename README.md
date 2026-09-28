# Sector Leaders Agent

**Sector Leaders** is a Python-based AI agent application that researches equity sectors and Sector Exchange Traded Funds (ETFs). It identifies top constituents (top 5 to top 10 holdings), extracts company names, ticker symbols, and portfolio weights, and generates clean ticker symbol sets formatted for downstream financial screeners and portfolio modeling.

---

## Features

- **Flexible Sector & ETF Input**: Accepts ETF ticker symbols (e.g. `XLF`, `XLK`, `XLE`) or general sector names (e.g. *Financials*, *Technology*, *Energy*).
- **Agentic Research**: Powered by the Google Gemini API (`google-genai`) with fallback support to `yfinance` data retrieval.
- **Top 10 Constituent Breakdown**: Extracts rank, ticker symbol, company name, weight percentage, and dynamic visual progress bars.
- **Formatted Symbol Sets**: Generates symbol set strings ready for copying (e.g., `XLF {BRK.B, JPM, V, MA, BAC, GS, WFC, PGR, KKR, SPGI}`).
- **Interactive Web UI**: Modern glassmorphic dark mode dashboard with quick-select sector chips and 1-click ticker copy.
- **CLI & REST API Support**: Available as a command-line utility (`main.py`) or a FastAPI web application (`app.py`).

---

## Project Structure

```text
sector_leaders/
├── main.py              # CLI entry point for sector research
├── app.py               # FastAPI web server & REST API
├── index.html           # Modern Glassmorphic Web UI
├── Spec.md              # Technical specification document
├── Sector Leaders.docx  # Original requirement document
├── requirements.txt     # Python dependencies
├── .env                 # Environment variables (API keys & models)
└── README.md            # Project documentation
```

---

## Setup & Installation

### 1. Prerequisites
- Python 3.10+
- Gemini API Key

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Configure Environment Variables
Create or verify the `.env` file in the project root:
```env
GEMINI_API_KEY=your_gemini_api_key_here
GEMINI_MODEL=gemini-2.5-flash
FALL_BACK_MODEL=gemini-2.5-flash-lite
PORT=8005
```

---

## Usage

### 1. Web Application
Launch the interactive web server:
```bash
python app.py
```
Open your browser and navigate to:
```text
http://localhost:8005
```

### 2. Command Line Interface (CLI)
Run `main.py` directly with an ETF ticker or sector name:
```bash
# Analyze XLF (Financials)
python main.py XLF

# Analyze Technology Sector
python main.py Technology
```

### 3. REST API Endpoint
Send a `POST` request to `/api/analyze`:
```bash
curl -X POST "http://localhost:8005/api/analyze" \
     -H "Content-Type: application/json" \
     -d '{"query": "XLK"}'
```

---

## Example Output

### Detailed Holdings
```text
Top 10 Holdings for XLF:
1. Berkshire Hathaway Inc. Class B (BRK.B): ~12.8%
2. JPMorgan Chase & Co. (JPM): ~10.2%
3. Visa Inc. Class A (V): ~8.1%
4. Mastercard Inc. Class A (MA): ~6.8%
5. Bank of America Corp. (BAC): ~4.6%
6. Goldman Sachs Group Inc. (GS): ~3.6%
7. Wells Fargo & Co. (WFC): ~3.3%
8. Progressive Corp. (PGR): ~2.6%
9. KKR & Co. Inc. (KKR): ~2.5%
10. S&P Global Inc. (SPGI): ~2.4%
```

### Symbol Set Output
```text
XLF {BRK.B, JPM, V, MA, BAC, GS, WFC, PGR, KKR, SPGI}
```
