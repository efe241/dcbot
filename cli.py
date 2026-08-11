import argparse
import asyncio
import sys
import os

from backend.manager import ProxyManager

async def main():
    parser = argparse.ArgumentParser(description="ProCheck CLI - Proxy Scraper & Checker")
    parser.add_argument("--scrape", action="store_true", help="Scrape fresh public proxies from internet")
    parser.add_argument("--check", action="store_true", help="Check scraped or input proxies")
    parser.add_argument("--input", type=str, default=None, help="Input TXT file containing IP:Port proxies")
    parser.add_argument("--output", type=str, default="data/proxies_alive.txt", help="Output file for alive proxies")
    parser.add_argument("--concurrency", type=int, default=150, help="Number of concurrent threads (default: 150)")
    parser.add_argument("--timeout", type=float, default=5.0, help="Connection timeout in seconds (default: 5.0)")
    parser.add_argument("--target", type=str, default="http://httpbin.org/ip", help="Target test URL")

    args = parser.parse_args()

    # If no flags passed, do both scrape & check by default
    do_scrape = args.scrape or (not args.scrape and not args.input)
    do_check = args.check or (not args.scrape and not args.input) or bool(args.input)

    manager = ProxyManager(data_dir="data")

    proxies_to_test = []

    if args.input and os.path.exists(args.input):
        print(f"[+] Reading proxies from custom file: {args.input}")
        with open(args.input, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if ":" in line:
                    parts = line.split(":")
                    proxies_to_test.append({"ip": parts[0].strip(), "port": int(parts[1].strip()), "protocol": "http"})
        print(f"[+] Loaded {len(proxies_to_test)} proxies from file.")
    elif do_scrape:
        print("[+] Scraping public proxy lists from 25+ internet sources...")
        proxies_to_test = await manager.scrape()
        print(f"[+] Scraped total {len(proxies_to_test)} unique proxies.")

    if do_check and proxies_to_test:
        print(f"[+] Starting check on {len(proxies_to_test)} proxies...")
        print(f"    Concurrency: {args.concurrency} | Timeout: {args.timeout}s | Target: {args.target}")

        def print_progress(result, stats):
            if result.get("alive"):
                print(f"  [ALIVE] {result['proxy']:<22} | {result['protocol'].upper():<6} | {result['latency']}ms | {result['anonymity']}")

        results = await manager.check(
            proxies=proxies_to_test,
            concurrency=args.concurrency,
            timeout=args.timeout,
            target_url=args.target,
            progress_cb=print_progress
        )

        alive = [r for r in results if r.get("alive")]
        print("\n" + "="*60)
        print(f"[Summary] Total Tested: {len(results)} | Working: {len(alive)} | Dead: {len(results) - len(alive)}")
        print(f"[Summary] Saved alive proxies to: {os.path.abspath(args.output)}")
        print("="*60)

if __name__ == "__main__":
    asyncio.run(main())
