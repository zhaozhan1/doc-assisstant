from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from app.ingestion.ingester import Ingester
from app.models.task import FileResult


class TestProcessFilesParallel:
    @pytest.mark.asyncio
    async def test_process_files_processes_all(self):
        ingester = Ingester.__new__(Ingester)
        ingester.vector_store = AsyncMock()

        with patch.object(ingester, "process_file", new_callable=AsyncMock) as mock_process:
            mock_process.return_value = FileResult(path="test.docx", status="success", chunks_count=1)

            paths = [Path(f"file_{i}.docx") for i in range(5)]
            results = await ingester.process_files(paths, max_concurrent=2)

            assert len(results) == 5
            assert all(r.status == "success" for r in results)
            assert mock_process.call_count == 5
