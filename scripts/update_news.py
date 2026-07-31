# -*- coding: utf-8 -*-
"""每日更新腳本 —— 由 GitHub Actions 排程執行，也可以在本機手動跑。

用法：
    python scripts/update_news.py                # 更新所有啟用中的主題
    python scripts/update_news.py --days 3       # 收錄最近 3 天
    python scripts/update_news.py --no-llm       # 不呼叫 Groq，用擷取式摘要
    python scripts/update_news.py --topic ai     # 只更新指定主題
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.stdout.reconfigure(encoding="utf-8")

from core import llm, pipeline, store, topics as topics_mod  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=int, default=2, help="收錄最近幾天的新聞")
    ap.add_argument("--limit", type=int, default=20, help="每個主題最多保留幾則")
    ap.add_argument("--no-llm", action="store_true", help="停用 Groq 摘要")
    ap.add_argument("--topic", action="append", help="只更新指定主題 id（可重複）")
    ap.add_argument("--keep-days", type=int, default=60, help="保留最近幾天的快照")
    args = ap.parse_args()

    active = topics_mod.enabled_topics()
    if args.topic:
        active = [t for t in active if t["id"] in args.topic]
    if not active:
        print("沒有啟用中的主題，結束。")
        return 1

    use_llm = (not args.no_llm) and llm.available()
    print(f"日期：{store.today_str()}")
    print(f"摘要模式：{'Groq ' + llm.MODEL if use_llm else '擷取式（無 LLM）'}")
    print(f"主題：{'、'.join(t['name'] for t in active)}")
    print("-" * 60)

    def progress(msg):
        print("  " + msg, flush=True)

    snap = pipeline.run_update(active, days=args.days, limit=args.limit,
                               use_llm=use_llm, progress=progress)

    print("-" * 60)
    total = 0
    for t in active:
        n = len(snap["topics"].get(t["id"], []))
        official = sum(1 for a in snap["topics"].get(t["id"], []) if a.get("official"))
        total += n
        print(f"  {t['name']}：{n} 則（官方 {official} 則）")
    print(f"合計 {total} 則，已寫入 {store.news_path(snap['date'])}")

    removed = store.prune_old_snapshots(args.keep_days)
    if removed:
        print(f"已清除舊快照：{'、'.join(removed)}")
    return 0 if total else 2


if __name__ == "__main__":
    sys.exit(main())
