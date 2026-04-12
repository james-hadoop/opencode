import os
import aiofiles
import uuid
from pathlib import Path
from typing import Optional
from datetime import datetime


class FileArtifactStorage:
    def __init__(self, root_dir: str = "/tmp/mineru-studio-artifacts"):
        self.root_dir = Path(root_dir)
        self.root_dir.mkdir(parents=True, exist_ok=True)

    def _get_artifact_path(self, run_id: str, node_id: str, filename: str) -> Path:
        return self.root_dir / run_id / node_id / filename

    async def save_artifact(
        self,
        run_id: str,
        node_id: str,
        filename: str,
        content: bytes,
        content_type: str = "application/octet-stream",
    ) -> dict:
        path = self._get_artifact_path(run_id, node_id, filename)
        path.parent.mkdir(parents=True, exist_ok=True)

        async with aiofiles.open(path, "wb") as f:
            await f.write(content)

        return {
            "artifact_id": f"art_{uuid.uuid4().hex[:12]}",
            "run_id": run_id,
            "node_id": node_id,
            "filename": filename,
            "path": str(path),
            "size_bytes": len(content),
            "content_type": content_type,
            "created_at": int(datetime.now().timestamp() * 1000),
        }

    async def get_artifact(self, run_id: str, node_id: str, filename: str) -> Optional[bytes]:
        path = self._get_artifact_path(run_id, node_id, filename)
        if not path.exists():
            return None
        async with aiofiles.open(path, "rb") as f:
            return await f.read()

    async def get_artifact_by_id(self, artifact_id: str) -> Optional[tuple[bytes, str]]:
        for run_dir in self.root_dir.iterdir():
            if not run_dir.is_dir():
                continue
            for node_dir in run_dir.iterdir():
                if not node_dir.is_dir():
                    continue
                for file in node_dir.iterdir():
                    if file.name.startswith(artifact_id.replace("art_", "")):
                        async with aiofiles.open(file, "rb") as f:
                            content = await f.read()
                        return content, file.name
        return None

    async def list_artifacts(self, run_id: str, node_id: Optional[str] = None) -> list[dict]:
        run_dir = self.root_dir / run_id
        if not run_dir.exists():
            return []

        artifacts = []
        for node_dir in run_dir.iterdir():
            if not node_dir.is_dir():
                continue
            if node_id and node_dir.name != node_id:
                continue
            for file in node_dir.iterdir():
                if file.is_file():
                    stat = file.stat()
                    artifacts.append({
                        "artifact_id": f"art_{file.name[:12]}",
                        "run_id": run_id,
                        "node_id": node_dir.name,
                        "filename": file.name,
                        "path": str(file),
                        "size_bytes": stat.st_size,
                        "content_type": "application/octet-stream",
                        "created_at": int(stat.st_mtime * 1000),
                    })
        return artifacts

    async def delete_artifact(self, run_id: str, node_id: str, filename: str) -> bool:
        path = self._get_artifact_path(run_id, node_id, filename)
        if path.exists():
            path.unlink()
            return True
        return False

    async def delete_artifacts_for_run(self, run_id: str) -> int:
        run_dir = self.root_dir / run_id
        if not run_dir.exists():
            return 0

        count = 0
        for file in run_dir.rglob("*"):
            if file.is_file():
                file.unlink()
                count += 1
        run_dir.rmdir()
        return count


artifact_storage = FileArtifactStorage()