"""导入压测：100/500/1000/5000 文档，记录耗时"""
import asyncio
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "backend"))


async def bench_import(data_dir: str, config_file: str | None = None, scales: list[int] | None = None):
    from app.config import AppConfig
    from app.ingestion.ingester import Ingester
    from app.llm.factory import create_embed_provider, create_provider
    from app.db.vector_store import VectorStore

    scales = scales or [100, 500, 1000, 5000]
    kwargs = {"_yaml_file": config_file} if config_file else {}
    config = AppConfig(**kwargs)
    llm = create_provider(config.llm)
    embed_llm = create_embed_provider(config.llm)

    vector_store = VectorStore(config.knowledge_base.db_path, embed_llm)
    ingester = Ingester(config, llm, vector_store)

    all_files = sorted(Path(data_dir).glob("*.txt"))

    for scale in scales:
        files = all_files[:scale]
        if len(files) < scale:
            print(f"跳过 {scale}: 文件不足 (需要 {scale}, 只有 {len(files)})")
            continue

        start = time.monotonic()
        semaphore = asyncio.Semaphore(4)
        results = []

        async def _process(path: Path) -> None:
            async with semaphore:
                r = await ingester.process_file(path)
                results.append(r)

        await asyncio.gather(*[_process(f) for f in files])
        elapsed = time.monotonic() - start

        success = sum(1 for r in results if r.status == "success")
        failed = sum(1 for r in results if r.status == "failed")
        total_chunks = sum(r.chunks_count for r in results)

        print(f"规模 {scale}: {elapsed:.1f}s, 成功 {success}, 失败 {failed}, 总分块 {total_chunks}")


if __name__ == "__main__":
    data_dir = sys.argv[1] if len(sys.argv) > 1 else "./data/perf_test"
    config_file = sys.argv[2] if len(sys.argv) > 2 else None
    asyncio.run(bench_import(data_dir, config_file))
