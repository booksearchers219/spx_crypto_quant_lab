import argparse
import multiprocessing
import sys


def main():
    parser = argparse.ArgumentParser(description="SPX + Crypto Quant Lab - Research Driven")
    parser.add_argument("--mode", choices=["research", "crypto", "equity", "all", "dashboard"],
                        default="research", help="What to run")
    parser.add_argument("--research_mode", choices=["equity", "crypto"],
                        default="equity", help="Which market to research")

    args = parser.parse_args()

    if args.mode == "research":
        print("🔬 Running Research...")
        from research.research_runner import run_research
        run_research(mode=args.research_mode)

    elif args.mode == "crypto":
        print("🚀 Starting Research-Driven Crypto Virtual Bot...")
        from live_trading.crypto_bot import run_crypto_cycle
        run_crypto_cycle()  # This starts the continuous loop

    elif args.mode == "equity":
        print("📈 Starting Research-Driven Equity Virtual Bot...")
        from live_trading.equity_bot import run_equity_cycle
        run_equity_cycle()

    elif args.mode == "dashboard":
        print("📊 Opening Dashboard...")
        from dashboard.portfolio_dashboard import show_dashboard
        show_dashboard()

    elif args.mode == "all":
        print("🚀 Starting ALL bots in parallel (Crypto 24/7 + Equity Market Hours)")
        from live_trading.crypto_bot import run_crypto_cycle
        from live_trading.equity_bot import run_equity_cycle

        p1 = multiprocessing.Process(target=run_crypto_cycle)
        p2 = multiprocessing.Process(target=run_equity_cycle)
        p1.start()
        p2.start()
        p1.join()
        p2.join()


if __name__ == "__main__":
    main()