import argparse
import multiprocessing


def main():
    parser = argparse.ArgumentParser(description="SPX + Crypto Quant Lab")
    parser.add_argument("--mode", choices=["research", "crypto", "equity", "all", "dashboard"],
                        default="research", help="What to run")
    parser.add_argument("--research_mode", choices=["equity", "crypto"],
                        default="equity", help="Which market to research")
    parser.add_argument("--reset", action="store_true", help="Reset both portfolios to $30,000")

    args = parser.parse_args()

    if args.reset:
        print("🔄 Resetting both portfolios to $30,000...")
        from risk.risk_manager import RiskManager
        RiskManager(capital=30000, name="crypto").reset()
        RiskManager(capital=30000, name="equity").reset()
        print("✅ Both bots have been reset to $30,000 each!")
        return

    if args.mode == "research":
        print("🔬 Running Research...")
        from research.research_runner import run_research
        run_research(mode=args.research_mode)

    elif args.mode == "crypto":
        print("🚀 Starting Crypto Bot...")
        from live_trading.crypto_bot import run_crypto_cycle
        run_crypto_cycle()

    elif args.mode == "equity":
        print("📈 Starting Equity Bot...")
        from live_trading.equity_bot import run_equity_cycle
        run_equity_cycle()

    elif args.mode == "dashboard":
        print("📊 Opening Dashboard...")
        from dashboard.portfolio_dashboard import show_dashboard
        show_dashboard()

    elif args.mode == "all":
        print("🚀 Starting ALL bots in parallel...")
        from live_trading.crypto_bot import run_crypto_cycle
        from live_trading.equity_bot import run_equity_cycle

        p1 = multiprocessing.Process(target=run_crypto_cycle)
        p2 = multiprocessing.Process(target=run_equity_cycle)
        p1.start()
        p2.start()
        try:
            p1.join()
            p2.join()
        except KeyboardInterrupt:
            print("\nStopping bots...")


if __name__ == "__main__":
    main()