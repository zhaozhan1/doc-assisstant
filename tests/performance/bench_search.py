"""检索压测：不同数据量下检索延迟"""
import asyncio
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "backend"))


async def bench_search(queries: list[str] | None = None, iterations: int = 5):
    from app.config import AppConfig
    from app.db.vector_store import VectorStore
    from app.llm.factory import create_embed_provider

    queries = queries or ["安全生产通知", "2026年工作总结", "信息化建设方案", "人才培养规划"]
    config = AppConfig()
    embed_llm = create_embed_provider(config.llm)
    vector_store = VectorStore(config.knowledge_base.db_path, embed_llm)

    for query in queries:
        times = []
        for _ in range(iterations):
            start = time.monotonic()
            results = await vector_store.search(query, top_k=10)
            elapsed = time.monotonic() - start
            times.append(elapsed)

        avg = sum(times) / len(times)
        print(f"查询 '{query}': 平均 {avg*1000:.0f}ms, 结果数 {len(results)}, 耗时 {[f'{t*1000:.0f}ms' for t in times]}")


if __name__ == "__main__":
    asyncio.run(bench_search())
