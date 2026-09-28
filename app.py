import os
import sys
import re
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import uvicorn
import yfinance as yf
from google import genai

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
PRIMARY_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash").strip()
FALLBACK_MODEL = os.getenv("FALL_BACK_MODEL", "gemini-2.5-flash-lite").strip()
PORT = int(os.getenv("PORT", 8005))

app = FastAPI(title="Sector Leaders Web API", version="1.0.0")

SECTOR_TO_ETF = {
    "FINANCIAL": "XLF",
    "FINANCIALS": "XLF",
    "FINANCIAL SERVICES": "XLF",
    "TECHNOLOGY": "XLK",
    "INFO TECH": "XLK",
    "INFORMATION TECHNOLOGY": "XLK",
    "ENERGY": "XLE",
    "HEALTHCARE": "XLV",
    "HEALTH CARE": "XLV",
    "CONSUMER DISCRETIONARY": "XLY",
    "CONSUMER STAPLES": "XLP",
    "INDUSTRIALS": "XLI",
    "UTILITIES": "XLU",
    "MATERIALS": "XLB",
    "REAL ESTATE": "XLRE",
    "COMMUNICATION SERVICES": "XLC",
    "COMMUNICATIONS": "XLC",
}

class AnalyzeRequest(BaseModel):
    query: str

def resolve_input(user_input: str) -> str:
    cleaned = user_input.strip().upper()
    return SECTOR_TO_ETF.get(cleaned, cleaned)

def get_holdings_via_yfinance(ticker_symbol: str) -> Optional[List[Dict[str, Any]]]:
    try:
        ticker = yf.Ticker(ticker_symbol)
        funds_data = ticker.funds_data
        if hasattr(funds_data, "top_holdings") and funds_data.top_holdings is not None:
            df = funds_data.top_holdings
            if not df.empty:
                holdings = []
                for symbol, row in df.iterrows():
                    holding_name = row.get("Holding Name", symbol)
                    percent = row.get("Holding Percent", 0)
                    weight_val = round(percent * 100, 2) if isinstance(percent, float) else 0.0
                    weight_str = f"~{weight_val}%" if weight_val > 0 else str(percent)
                    holdings.append({
                        "symbol": str(symbol).replace("-", "."),
                        "name": str(holding_name),
                        "weight": weight_str,
                        "weight_val": weight_val
                    })
                return holdings[:10]
    except Exception as e:
        print(f"[Debug] yfinance lookup error: {e}", file=sys.stderr)
    return None

def query_gemini_agent(query: str, resolved_etf: str) -> Dict[str, Any]:
    if not GEMINI_API_KEY:
        raise ValueError("GEMINI_API_KEY is not configured in .env")
        
    client = genai.Client(api_key=GEMINI_API_KEY)
    
    prompt = f"""
You are an expert financial research agent.
The user wants top 10 constituent holdings for sector/ETF: '{query}' (Resolved Symbol: {resolved_etf}).

Perform research and return the top 10 constituents.
Strictly output your response in JSON format with the following keys:
{{
  "etf": "{resolved_etf}",
  "description": "Short 1-sentence summary of the sector or ETF",
  "holdings": [
    {{
      "rank": 1,
      "symbol": "TICKER",
      "name": "Company Full Name",
      "weight_percent": 12.5
    }}
  ],
  "symbol_set": "{resolved_etf} {{TICKER1, TICKER2, TICKER3, ...}}"
}}

Ensure there are top 10 items in the holdings list if data exists.
Return valid raw JSON only, wrapped in ```json ``` markdown block.
"""

    models_to_try = [PRIMARY_MODEL, FALLBACK_MODEL, "gemini-2.5-flash", "gemini-1.5-flash"]
    last_error = None

    for model in models_to_try:
        try:
            response = client.models.generate_content(
                model=model,
                contents=prompt
            )
            text = response.text.strip() if response and response.text else ""
            # Extract JSON block
            json_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
            if json_match:
                import json
                parsed = json.loads(json_match.group(1))
                return parsed
            elif text.startswith("{"):
                import json
                return json.loads(text)
        except Exception as e:
            last_error = e
            print(f"[Warning] Model {model} failed: {e}", file=sys.stderr)
            
    raise RuntimeError(f"Gemini agent failed: {last_error}")


@app.post("/api/analyze")
async def analyze_sector(req: AnalyzeRequest):
    query = req.query.strip()
    if not query:
        raise HTTPException(status_code=400, detail="Query cannot be empty.")
        
    resolved_etf = resolve_input(query)
    
    # 1. Try Gemini Agent for structured research
    try:
        ai_data = query_gemini_agent(query, resolved_etf)
        # Format holdings
        formatted_holdings = []
        symbols_list = []
        for idx, item in enumerate(ai_data.get("holdings", []), 1):
            sym = str(item.get("symbol", "")).upper()
            symbols_list.append(sym)
            w_val = float(item.get("weight_percent", 0.0))
            formatted_holdings.append({
                "rank": idx,
                "symbol": sym,
                "name": item.get("name", sym),
                "weight": f"~{w_val:.1f}%",
                "weight_val": w_val
            })
            
        sym_set = ai_data.get("symbol_set")
        if not sym_set or "{" not in sym_set:
            sym_set = f"{resolved_etf} {{{', '.join(symbols_list)}}}"
            
        return {
            "success": True,
            "query": query,
            "etf": resolved_etf,
            "description": ai_data.get("description", f"Top constituent holdings for {resolved_etf}"),
            "symbol_set": sym_set,
            "holdings": formatted_holdings,
            "source": "AI Agent"
        }
    except Exception as ai_err:
        print(f"[Fallback] Gemini AI query exception: {ai_err}", file=sys.stderr)

    # 2. Fallback to yfinance
    yf_data = get_holdings_via_yfinance(resolved_etf)
    if yf_data:
        symbols_list = [h["symbol"] for h in yf_data]
        sym_set = f"{resolved_etf} {{{', '.join(symbols_list)}}}"
        formatted = []
        for idx, h in enumerate(yf_data, 1):
            formatted.append({
                "rank": idx,
                "symbol": h["symbol"],
                "name": h["name"],
                "weight": h["weight"],
                "weight_val": h["weight_val"]
            })
        return {
            "success": True,
            "query": query,
            "etf": resolved_etf,
            "description": f"Top holdings for {resolved_etf} ETF",
            "symbol_set": sym_set,
            "holdings": formatted,
            "source": "Financial Data API"
        }

    raise HTTPException(status_code=404, detail=f"Could not find sector holdings for '{query}'. Please try a valid ETF ticker like XLF or sector name like Financials.")


@app.get("/", response_class=HTMLResponse)
async def get_index():
    with open("index.html", "r", encoding="utf-8") as f:
        return f.read()

if __name__ == "__main__":
    print(f"Starting Sector Leaders Web Server on http://localhost:{PORT}")
    uvicorn.run("app:app", host="127.0.0.1", port=PORT, reload=True)

