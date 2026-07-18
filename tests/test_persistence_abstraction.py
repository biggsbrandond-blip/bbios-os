import json
import tempfile
import unittest
from pathlib import Path
from typing import Any, Dict, List, Optional
from unittest.mock import patch

from bbi_os.client_execution.models import ClientExecutionRecord, StateTransition
from bbi_os.client_execution.service import ClientExecutionService
from bbi_os.client_execution.state import ExecutionStateRepository
from bbi_os.client_monetization.models import ClientPlan, UsageEvent
from bbi_os.client_monetization.pricing_engine import PricingEngine
from bbi_os.client_monetization.registry import ClientPlanRegistry
from bbi_os.client_monetization.service import ClientMonetizationService
from bbi_os.client_monetization.usage_tracker import UsageTracker
from bbi_os.domain import BaseEntity
from bbi_os.entity_repository import EntityRepository, JsonEntityRepository
from bbi_os.persistence import (
    ClientPlanRepository,
    ExecutionStateRepositoryContract,
    TaskRepository,
    UsageRepository,
)
from bbi_os.task_management.repository import JsonTaskRepository
from bbi_os.task_management.service import TaskService


class InMemoryTaskRepository:
    def __init__(self) -> None:
        self.records: Dict[str, Dict[str, Any]] = {}

    def list(self) -> List[Dict[str, Any]]:
        return list(self.records.values())

    def get(self, task_id: str) -> Optional[Dict[str, Any]]:
        return self.records.get(task_id)

    def exists(self, task_id: str) -> bool:
        return task_id in self.records

    def count(self) -> int:
        return len(self.records)

    def save(self, task: Dict[str, Any]) -> Dict[str, Any]:
        self.records[task["id"]] = dict(task)
        return self.records[task["id"]]

    def delete(self, task_id: str) -> bool:
        return self.records.pop(task_id, None) is not None


class FakeClients:
    entity_type = "client"

    def __init__(self) -> None:
        self.entity = BaseEntity(
            "client-1",
            "client",
            "2026-07-18T00:00:00Z",
            "2026-07-18T00:00:00Z",
            {},
        )

    def list(self) -> List[BaseEntity]:
        return [self.entity]

    def get(self, entity_id: str) -> Optional[BaseEntity]:
        return self.entity if entity_id == self.entity.entity_id else None

    def exists(self, entity_id: str) -> bool:
        return self.get(entity_id) is not None

    def count(self) -> int:
        return 1

    def save(self, entity: BaseEntity) -> BaseEntity:
        self.entity = entity
        return entity

    def delete(self, entity_id: str) -> bool:
        return entity_id == self.entity.entity_id


class FakePlans:
    def plan_for(self, client_id: str) -> ClientPlan:
        return ClientPlan("pro", 100, True, 10, 10)

    def assign(self, client_id: str, plan_id: str) -> ClientPlan:
        return self.plan_for(client_id)


class FakeUsage:
    def __init__(self) -> None:
        self.events: List[UsageEvent] = []

    def record(self, event: UsageEvent) -> UsageEvent:
        self.events.append(event)
        return event

    def for_client(self, client_id: str) -> List[UsageEvent]:
        return [event for event in self.events if event.client_id == client_id]

    def total_units(self, client_id: str) -> int:
        return sum(event.usage_units for event in self.for_client(client_id))

    def recent_count(self, client_id: str, minutes: int = 1) -> int:
        return len(self.for_client(client_id))


class FakeExecutionState:
    def __init__(self, record: ClientExecutionRecord) -> None:
        self.record = record

    def save(self, record: ClientExecutionRecord) -> ClientExecutionRecord:
        self.record = record
        return record

    def get(self, execution_id: str) -> Optional[ClientExecutionRecord]:
        return self.record if execution_id == self.record.execution_id else None

    def exists(self, execution_id: str) -> bool:
        return self.get(execution_id) is not None

    def count(self) -> int:
        return 1

    def list(self) -> List[ClientExecutionRecord]:
        return [self.record]

    def latest_for_client(self, client_id: str) -> Optional[ClientExecutionRecord]:
        return self.record if client_id == self.record.client_id else None

    def list_for_client(self, client_id: str) -> List[ClientExecutionRecord]:
        return [self.record] if client_id == self.record.client_id else []


class PersistenceAbstractionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary_directory.name)

    def tearDown(self) -> None:
        self.temporary_directory.cleanup()

    def test_json_repositories_satisfy_runtime_protocols(self) -> None:
        self.assertIsInstance(
            JsonTaskRepository(self.root / "tasks.json"), TaskRepository
        )
        entity_repository: EntityRepository = JsonEntityRepository(
            "client", self.root / "clients.json"
        )
        self.assertEqual("client", entity_repository.entity_type)
        self.assertEqual(0, entity_repository.count())
        self.assertIsInstance(
            ExecutionStateRepository(self.root / "executions.json"),
            ExecutionStateRepositoryContract,
        )
        self.assertIsInstance(
            ClientPlanRegistry(self.root / "plans.json"), ClientPlanRepository
        )
        self.assertIsInstance(UsageTracker(self.root / "usage.json"), UsageRepository)

    def test_task_service_accepts_repository_protocol_substitute(self) -> None:
        service = TaskService(InMemoryTaskRepository())
        with patch("bbi_os.task_management.service.uuid4", return_value="task-1"), patch(
            "bbi_os.task_management.service._timestamp",
            side_effect=["2026-07-18T00:00:00Z", "2026-07-18T00:01:00Z"],
        ):
            created = service.create(
                {"title": "Protocol", "description": "Substitute", "status": "pending"}
            )
            updated = service.update(created["id"], {"status": "complete"})

        self.assertEqual("task-1", created["id"])
        self.assertEqual("complete", updated["status"])
        self.assertEqual([updated], service.list())
        service.delete("task-1")
        self.assertEqual([], service.list())

    def test_task_service_json_persistence_output_is_unchanged(self) -> None:
        service = TaskService(JsonTaskRepository(self.root / "tasks.json"))
        with patch("bbi_os.task_management.service.uuid4", return_value="task-1"), patch(
            "bbi_os.task_management.service._timestamp",
            return_value="2026-07-18T00:00:00Z",
        ):
            created = service.create(
                {"title": "JSON", "description": "Same shape", "status": "pending"}
            )

        with (self.root / "tasks.json").open(encoding="utf-8") as data_file:
            self.assertEqual({"task-1": created}, json.load(data_file))

    def test_execution_service_accepts_state_repository_protocol(self) -> None:
        record = ClientExecutionRecord(
            execution_id="execution-1",
            client_id="client-1",
            execution_type="one_time",
            workflow_id="workflow-1",
            input_data={},
            state="COMPLETED",
            transitions=[StateTransition("COMPLETED", "2026-07-18T00:00:00Z")],
            created_at="2026-07-18T00:00:00Z",
            updated_at="2026-07-18T00:00:00Z",
        )
        service = ClientExecutionService(
            FakeClients(), object(), object(), FakeExecutionState(record)  # type: ignore[arg-type]
        )

        self.assertEqual(record, service.get_execution("execution-1"))
        self.assertIsNone(service.get_execution("missing"))

    def test_monetization_service_accepts_plan_and_usage_protocols(self) -> None:
        usage = FakeUsage()
        service = ClientMonetizationService(
            FakeClients(),  # type: ignore[arg-type]
            FakePlans(),  # type: ignore[arg-type]
            usage,  # type: ignore[arg-type]
            PricingEngine(),
        )

        event = service.record_automatic("client-1", "workflow_execution", 2, {})

        self.assertEqual("client-1", event.client_id)
        self.assertEqual([event], usage.events)


if __name__ == "__main__":
    unittest.main()
