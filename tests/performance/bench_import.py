"""导入压测：100/500/1000/5000 文档，记录耗时和内存"""
import asyncio
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "backend"))


async def bench_import(data_dir: str, scales: list[int] | None = None):
    from app.config import AppConfig
    from app.ingestion.ingester import Ingester
    from app.llm.factory import create_embed_provider, create_provider

    scales = scales or [100, 500, 1000, 5000]
    config = AppConfig()
    llm = create_provider(config.llm)
    embed_llm = create_embed_provider(config.llm)

    from app.db.vector_store import VectorStore
    vector_store = VectorStore(config.knowledge_base.db_path, embed_llm)
    ingester = Ingester(config, llm, vector_store)

    all_files = sorted(Path(data_dir).glob("*.txt"))

    for scale in scales:
        files = all_files[:scale]
        if len(files) < scale:
            print(f"跳过 {scale}: 文件不足 (需要 {scale}, 只有 {len(files)})")
            continue

        start = time.monotonic()
        results = await ingester.process_files(files, max_concurrent=4)
        elapsed = time.monotonic() - start

        success = sum(1 for r in results if r.status == "success")
        failed = sum(1 for r in results if r.status == "failed")
        total_chunks = sum(r.chunks_count for r in results)

        print(f"规模 {scale}: {elapsed:.1f}s, 成功 {success}, 失败 {failed}, 总分块 {total_chunks}")


if __name__ == "__main__":
    data_dir = sys.argv[1] if len(sys.argv) > 1 else "./data/perf_test"
    asyncio.run(bench_import(data_dir))
