import os
import sys
import re
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv
import yfinance as yf
from google import genai
from google.genai import types

# Load environment variables
load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
PRIMARY_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash").strip()
FALLBACK_MODEL = os.getenv("FALL_BACK_MODEL", "gemini-2.5-flash-lite").strip()

# Map common sector names to SPDR Sector ETFs
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


def resolve_input(user_input: str) -> str:
    """Resolves sector name to ETF symbol or normalizes ETF symbol."""
    cleaned = user_input.strip().upper()
    if cleaned in SECTOR_TO_ETF:
        return SECTOR_TO_ETF[cleaned]
    return cleaned


def get_holdings_via_yfinance(ticker_symbol: str) -> Optional[List[Dict[str, Any]]]:
    """Attempts to fetch top holdings using yfinance."""
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
                    if isinstance(percent, float):
                        percent_str = f"~{percent * 100:.1f}%"
                    else:
                        percent_str = str(percent)
                    holdings.append({
                        "symbol": str(symbol).replace("-", "."),
                        "name": str(holding_name),
                        "weight": percent_str
                    })
                return holdings[:10]
    except Exception as e:
        print(f"[Debug] yfinance lookup error: {e}", file=sys.stderr)
    return None


def get_holdings_via_gemini(query: str) -> str:
    """Uses Gemini API to research top holdings for the given ETF/Sector."""
    client = genai.Client(api_key=GEMINI_API_KEY)
    
    prompt = f"""
You are an expert financial research agent.
The user is asking for the top 10 constituent holdings of the ETF or sector: '{query}'.

Please provide:
1. The top 10 holdings with company names, stock tickers, and approximate weight percentages.
2. A single clean line listing the ticker symbols in set notation format:
   ETF_TICKER {{TICKER1, TICKER2, TICKER3, ...}}

Example format for XLF:
Top 10 Holdings
Berkshire Hathaway Inc. (BRK.B): ~12.2%
JPMorgan Chase & Co. (JPM): ~11.7%
Visa Inc. (V): ~8.1%
Mastercard Inc. (MA): ~5.9%
Bank of America Corp. (BAC): ~4.7%
Goldman Sachs Group Inc. (GS): ~3.5%
Wells Fargo & Co. (WFC): ~3.2%
Morgan Stanley (MS): ~3.1%
Citigroup Inc. (C): ~2.9%
Charles Schwab Corp. (SCHW): ~2.1%

Create a list of the stock symbols - XLF {{BRK.B, JPM, V, MA, BAC, GS, WFC, MS, C, SCHW}}
"""

    models_to_try = [PRIMARY_MODEL, FALLBACK_MODEL, "gemini-2.5-flash", "gemini-1.5-flash"]
    last_error = None
    
    for model in models_to_try:
        try:
            print(f"[Info] Querying agent model: {model}...")
            response = client.models.generate_content(
                model=model,
                contents=prompt
            )
            if response.text:
                return response.text.strip()
        except Exception as e:
            last_error = e
            print(f"[Warning] Model {model} failed: {e}. Trying fallback...", file=sys.stderr)
            
    raise RuntimeError(f"All Gemini model attempts failed. Last error: {last_error}")


def main():
    print("=========================================")
    print("      Sector Leaders Research Agent      ")
    print("=========================================\n")
    
    if len(sys.argv) > 1:
        user_input = " ".join(sys.argv[1:])
    else:
        user_input = input("Enter ETF Ticker or Sector Name (e.g. XLF, Financials): ").strip()
        
    if not user_input:
        print("No input provided. Exiting.")
        return

    etf_symbol = resolve_input(user_input)
    print(f"\n[Processing] Analyzing sector/ETF target: '{user_input}' (Resolved ETF: {etf_symbol})...\n")

    # Try Gemini Agent first for research
    try:
        result = get_holdings_via_gemini(etf_symbol)
        print(result)
        return
    except Exception as e:
        print(f"[Notice] Gemini search unavailable ({e}), falling back to direct yfinance data lookup...", file=sys.stderr)

    # Fallback to yfinance data lookup
    yf_holdings = get_holdings_via_yfinance(etf_symbol)
    if yf_holdings:
        print("Top 10 Holdings")
        symbols = []
        for h in yf_holdings:
            print(f"{h['name']} ({h['symbol']}): {h['weight']}")
            symbols.append(h['symbol'])
        symbols_set = ", ".join(symbols)
        print(f"\nCreate a list of the stock symbols - {etf_symbol} {{{symbols_set}}}")
    else:
        print(f"Unable to fetch holdings for '{user_input}'. Please verify the ticker or try again.")


if __name__ == "__main__":
    main()
