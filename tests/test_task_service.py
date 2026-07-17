import json
import tempfile
import unittest
from pathlib import Path

from bbi_os.task_management.errors import TaskNotFoundError, ValidationError
from bbi_os.task_management.repository import JsonTaskRepository
from bbi_os.task_management.service import TaskService


class TaskServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.data_file = Path(self.temporary_directory.name) / "tasks.json"
        self.service = TaskService(JsonTaskRepository(self.data_file))

    def tearDown(self) -> None:
        self.temporary_directory.cleanup()

    def test_crud_operations_and_persistence(self) -> None:
        created = self.service.create(
            {"title": "Test", "description": "Test CRUD", "status": "pending"}
        )
        self.assertEqual(created, self.service.get(created["id"]))
        self.assertEqual([created], self.service.list())

        updated = self.service.update(created["id"], {"status": "complete"})
        self.assertEqual("complete", updated["status"])
        self.assertEqual(created["created_at"], updated["created_at"])
        self.assertIn("updated_at", updated)

        restarted_service = TaskService(JsonTaskRepository(self.data_file))
        self.assertEqual(updated, restarted_service.get(created["id"]))

        restarted_service.delete(created["id"])
        self.assertEqual([], restarted_service.list())
        with self.assertRaises(TaskNotFoundError):
            restarted_service.get(created["id"])

    def test_unique_ids(self) -> None:
        data = {"title": "Task", "description": "Description", "status": "pending"}
        self.assertNotEqual(self.service.create(data)["id"], self.service.create(data)["id"])

    def test_rejects_invalid_create_and_update_data(self) -> None:
        with self.assertRaises(ValidationError):
            self.service.create({"title": "Missing fields"})
        with self.assertRaises(ValidationError):
            self.service.create(
                {"title": "Task", "description": "Description", "status": "invalid"}
            )
        task = self.service.create(
            {"title": "Task", "description": "Description", "status": "pending"}
        )
        with self.assertRaises(ValidationError):
            self.service.update(task["id"], {"id": "replacement"})

    def test_data_file_is_valid_json(self) -> None:
        task = self.service.create(
            {"title": "Task", "description": "Description", "status": "pending"}
        )
        with self.data_file.open(encoding="utf-8") as data_file:
            self.assertEqual(task, json.load(data_file)[task["id"]])


if __name__ == "__main__":
    unittest.main()
