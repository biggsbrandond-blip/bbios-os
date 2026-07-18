import tempfile
import unittest
from pathlib import Path

from bbi_os.client_execution.models import (
    ClientExecutionRecord,
    StateTransition,
)
from bbi_os.client_execution.state import ExecutionStateRepository
from bbi_os.domain import BaseEntity
from bbi_os.entity_repository import JsonEntityRepository
from bbi_os.task_management.repository import JsonTaskRepository


class RepositoryContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_task_repository_exposes_exists_and_count_without_changing_crud(self) -> None:
        repository = JsonTaskRepository(self.root / "tasks.json")
        task = {
            "id": "task-1",
            "title": "Prepare release",
            "description": "Validate repository contracts",
            "status": "pending",
            "created_at": "2026-01-01T00:00:00Z",
            "updated_at": "2026-01-01T00:00:00Z",
        }

        self.assertFalse(repository.exists("task-1"))
        self.assertEqual(repository.count(), 0)
        self.assertEqual(repository.save(task), task)
        self.assertTrue(repository.exists("task-1"))
        self.assertEqual(repository.count(), 1)
        self.assertEqual(repository.get("task-1"), task)
        self.assertEqual(repository.list(), [task])
        self.assertTrue(repository.delete("task-1"))
        self.assertFalse(repository.exists("task-1"))
        self.assertEqual(repository.count(), 0)

    def test_entity_repository_exposes_exists_and_count_without_changing_crud(self) -> None:
        repository = JsonEntityRepository("client", self.root / "clients.json")
        entity = BaseEntity(
            entity_id="client-1",
            entity_type="client",
            created_at="2026-01-01T00:00:00Z",
            updated_at="2026-01-01T00:00:00Z",
            metadata={"name": "Biggs Bold Ink"},
        )

        self.assertFalse(repository.exists("client-1"))
        self.assertEqual(repository.count(), 0)
        self.assertEqual(repository.save(entity), entity)
        self.assertTrue(repository.exists("client-1"))
        self.assertEqual(repository.count(), 1)
        self.assertEqual(repository.get("client-1"), entity)
        self.assertEqual(repository.list(), [entity])
        self.assertTrue(repository.delete("client-1"))
        self.assertFalse(repository.exists("client-1"))
        self.assertEqual(repository.count(), 0)

    def test_execution_state_repository_exposes_exists_and_count_without_changing_reads(
        self,
    ) -> None:
        repository = ExecutionStateRepository(self.root / "executions.json")
        record = ClientExecutionRecord(
            execution_id="execution-1",
            client_id="client-1",
            execution_type="one_time",
            workflow_id="workflow-1",
            input_data={"priority": "normal"},
            state="PENDING",
            transitions=[StateTransition("PENDING", "2026-01-01T00:00:00Z")],
            created_at="2026-01-01T00:00:00Z",
            updated_at="2026-01-01T00:00:00Z",
        )

        self.assertFalse(repository.exists("execution-1"))
        self.assertEqual(repository.count(), 0)
        self.assertEqual(repository.save(record), record)
        self.assertTrue(repository.exists("execution-1"))
        self.assertEqual(repository.count(), 1)
        self.assertEqual(repository.get("execution-1"), record)
        self.assertEqual(repository.list(), [record])
        self.assertEqual(repository.list_for_client("client-1"), [record])
        self.assertEqual(repository.latest_for_client("client-1"), record)


if __name__ == "__main__":
    unittest.main()
