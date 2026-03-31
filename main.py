import argparse
from research.research_runner import run_research
from live_trading.crypto_bot import run_crypto_bot
from live_trading.equity_bot import run_equity_bot
import multiprocessing

def main():
    parser = argparse.ArgumentParser(description="SPX + Crypto Quant Lab")
    parser.add_argument("--mode", choices=["research", "crypto", "equity", "all"], default="research",
                        help="Mode to run")
    parser.add_argument("--research_mode", choices=["equity", "crypto"], default="equity",
                        help="Which watchlist to research")
    
    args = parser.parse_args()

    if args.mode == "research":
        run_research(mode=args.research_mode)
        
    elif args.mode == "crypto":
        print("🚀 Starting Crypto 24/7 Bot...")
        run_crypto_bot()
        
    elif args.mode == "equity":
        print("📈 Starting Equity Market-Hours Bot...")
        run_equity_bot()
        
    elif args.mode == "all":
        print("Starting all bots in parallel...")
        p1 = multiprocessing.Process(target=run_crypto_bot)
        p2 = multiprocessing.Process(target=run_equity_bot)
        p1.start()
        p2.start()
        p1.join()
        p2.join()

if __name__ == "__main__":
    main()
