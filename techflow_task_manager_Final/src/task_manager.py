"""Módulo de gerenciamento de tarefas logísticas da TechFlow Solutions com persistência SQLite."""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
import sqlite3
from typing import Dict, List, Optional


VALID_STATUSES = ("A Fazer", "Em Progresso", "Concluído")
VALID_PRIORITIES = ("Baixa", "Média", "Alta", "Crítica")
CRITICAL_SLA_THRESHOLD_HOURS = 4


@dataclass
class Task:
    """Representa uma tarefa operacional no fluxo logístico."""

    id: int
    title: str
    description: str = ""
    status: str = "A Fazer"
    priority: str = "Média"
    assignee: str = "Não atribuído"
    logistics_hub: str = "Hub Central"
    sla_hours: int = 24
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    @property
    def is_critical_alert(self) -> bool:
        """Indica se a tarefa exige alerta imediato (apenas tarefas não concluídas)."""
        if self.status == "Concluído":
            return False
        return self.priority == "Crítica" or self.sla_hours <= CRITICAL_SLA_THRESHOLD_HOURS

    @property
    def critical_reason(self) -> str:
        """Explica o motivo do alerta crítico para exibição clara na interface."""
        if not self.is_critical_alert:
            return ""
        reasons = []
        if self.priority == "Crítica":
            reasons.append("Prioridade Crítica")
        if self.sla_hours <= CRITICAL_SLA_THRESHOLD_HOURS:
            reasons.append(f"SLA <= {CRITICAL_SLA_THRESHOLD_HOURS}h ({self.sla_hours}h)")
        return " + ".join(reasons)


class TaskManager:
    """Gerencia o ciclo de vida das tarefas com armazenamento persistente em SQLite."""

    def __init__(self, db_path: str = "data/techflow_tasks.db") -> None:
        self.db_path = db_path
        if db_path != ":memory:":
            Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(db_path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._init_db()

    def _init_db(self) -> None:
        """Cria as tabelas de tarefas e metadados do sistema se ainda não existirem."""
        with self._conn:
            self._conn.execute(
                """
                CREATE TABLE IF NOT EXISTS tasks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    description TEXT NOT NULL DEFAULT '',
                    status TEXT NOT NULL DEFAULT 'A Fazer',
                    priority TEXT NOT NULL DEFAULT 'Média',
                    assignee TEXT NOT NULL DEFAULT 'Não atribuído',
                    logistics_hub TEXT NOT NULL DEFAULT 'Hub Central',
                    sla_hours INTEGER NOT NULL DEFAULT 24,
                    created_at TEXT NOT NULL
                )
                """
            )
            self._conn.execute(
                """
                CREATE TABLE IF NOT EXISTS app_meta (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                )
                """
            )

    def close(self) -> None:
        """Fecha a conexão com o banco SQLite."""
        self._conn.close()

    def seed_once(self) -> bool:
        """Popula exemplos iniciais APENAS na primeira inicialização do banco."""
        cur = self._conn.execute("SELECT value FROM app_meta WHERE key = 'initial_seed_done'")
        if cur.fetchone() is not None:
            return False

        self.create_task(
            title="Conferir manifesto de carga - Rota SP-RJ",
            description="Validar notas fiscais e lacres antes da saída do caminhão.",
            status="Concluído",
            priority="Alta",
            assignee="Ana Silva",
            logistics_hub="CD Guarulhos",
            sla_hours=6,
        )
        self.create_task(
            title="Resolver divergência de estoque no Hub Sul",
            description="Investigar diferença de 14 volumes no inventário matinal.",
            status="Em Progresso",
            priority="Crítica",
            assignee="Carlos Souza",
            logistics_hub="Hub Sul",
            sla_hours=3,
        )
        self.create_task(
            title="Atualizar status de entrega - Cliente LogExpress",
            description="Sincronizar comprovante de entrega com o painel do cliente.",
            status="A Fazer",
            priority="Média",
            assignee="Beatriz Lima",
            logistics_hub="Hub Central",
            sla_hours=12,
        )

        with self._conn:
            self._conn.execute(
                "INSERT INTO app_meta (key, value) VALUES ('initial_seed_done', '1')"
            )
        return True

    @staticmethod
    def _row_to_task(row: sqlite3.Row) -> Task:
        return Task(
            id=row["id"],
            title=row["title"],
            description=row["description"],
            status=row["status"],
            priority=row["priority"],
            assignee=row["assignee"],
            logistics_hub=row["logistics_hub"],
            sla_hours=row["sla_hours"],
            created_at=row["created_at"],
        )

    @staticmethod
    def _validate_title(title: str) -> str:
        if not isinstance(title, str) or not title.strip():
            raise ValueError("O título da tarefa é obrigatório e não pode estar vazio.")
        cleaned = title.strip()
        if len(cleaned) > 120:
            raise ValueError("O título da tarefa deve ter no máximo 120 caracteres.")
        return cleaned

    @staticmethod
    def _validate_status(status: str) -> str:
        if status not in VALID_STATUSES:
            raise ValueError(f"Status inválido '{status}'. Use um de: {', '.join(VALID_STATUSES)}.")
        return status

    @staticmethod
    def _validate_priority(priority: str) -> str:
        if priority not in VALID_PRIORITIES:
            raise ValueError(
                f"Prioridade inválida '{priority}'. Use uma de: {', '.join(VALID_PRIORITIES)}."
            )
        return priority

    @staticmethod
    def _validate_sla(sla_hours: int) -> int:
        if not isinstance(sla_hours, int) or isinstance(sla_hours, bool) or sla_hours <= 0:
            raise ValueError("O SLA deve ser um número inteiro positivo de horas.")
        return sla_hours

    def create_task(
        self,
        title: str,
        description: str = "",
        status: str = "A Fazer",
        priority: str = "Média",
        assignee: str = "Não atribuído",
        logistics_hub: str = "Hub Central",
        sla_hours: int = 24,
    ) -> Task:
        """Cria e persiste uma nova tarefa no SQLite após validar os campos."""
        valid_title = self._validate_title(title)
        valid_status = self._validate_status(status)
        valid_priority = self._validate_priority(priority)
        valid_sla = self._validate_sla(sla_hours)

        clean_desc = description.strip()
        clean_assignee = assignee.strip() or "Não atribuído"
        clean_hub = logistics_hub.strip() or "Hub Central"
        created_at = datetime.now(timezone.utc).isoformat()

        with self._conn:
            cursor = self._conn.execute(
                """
                INSERT INTO tasks (title, description, status, priority, assignee, logistics_hub, sla_hours, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    valid_title,
                    clean_desc,
                    valid_status,
                    valid_priority,
                    clean_assignee,
                    clean_hub,
                    valid_sla,
                    created_at,
                ),
            )
            task_id = cursor.lastrowid

        return self.get_task(int(task_id))

    def list_tasks(
        self,
        status: Optional[str] = None,
        priority: Optional[str] = None,
        logistics_hub: Optional[str] = None,
    ) -> List[Task]:
        """Retorna tarefas persistidas filtradas opcionalmente por status, prioridade ou hub."""
        if status is not None:
            self._validate_status(status)
        if priority is not None:
            self._validate_priority(priority)

        query = "SELECT * FROM tasks WHERE 1=1"
        params: List[object] = []

        if status is not None:
            query += " AND status = ?"
            params.append(status)
        if priority is not None:
            query += " AND priority = ?"
            params.append(priority)
        if logistics_hub is not None:
            query += " AND LOWER(logistics_hub) = LOWER(?)"
            params.append(logistics_hub.strip())

        query += " ORDER BY id ASC"
        rows = self._conn.execute(query, params).fetchall()
        return [self._row_to_task(row) for row in rows]

    def get_task(self, task_id: int) -> Task:
        """Busca uma tarefa pelo ID no banco ou lança KeyError se não existir."""
        row = self._conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
        if row is None:
            raise KeyError(f"Tarefa com ID {task_id} não encontrada.")
        return self._row_to_task(row)

    def update_task(
        self,
        task_id: int,
        title: Optional[str] = None,
        description: Optional[str] = None,
        status: Optional[str] = None,
        priority: Optional[str] = None,
        assignee: Optional[str] = None,
        logistics_hub: Optional[str] = None,
        sla_hours: Optional[int] = None,
    ) -> Task:
        """Atualiza campos de uma tarefa existente no banco."""
        task = self.get_task(task_id)

        new_title = self._validate_title(title) if title is not None else task.title
        new_desc = description.strip() if description is not None else task.description
        new_status = self._validate_status(status) if status is not None else task.status
        new_priority = self._validate_priority(priority) if priority is not None else task.priority
        new_assignee = (assignee.strip() or "Não atribuído") if assignee is not None else task.assignee
        new_hub = (logistics_hub.strip() or "Hub Central") if logistics_hub is not None else task.logistics_hub
        new_sla = self._validate_sla(sla_hours) if sla_hours is not None else task.sla_hours

        with self._conn:
            self._conn.execute(
                """
                UPDATE tasks
                SET title = ?, description = ?, status = ?, priority = ?,
                    assignee = ?, logistics_hub = ?, sla_hours = ?
                WHERE id = ?
                """,
                (new_title, new_desc, new_status, new_priority, new_assignee, new_hub, new_sla, task_id),
            )

        return self.get_task(task_id)

    def delete_task(self, task_id: int) -> None:
        """Remove uma tarefa pelo ID no banco."""
        self.get_task(task_id)
        with self._conn:
            self._conn.execute("DELETE FROM tasks WHERE id = ?", (task_id,))

    def get_metrics(self) -> Dict[str, object]:
        """Calcula indicadores de fluxo e lista tarefas críticas pendentes."""
        all_tasks = self.list_tasks()
        by_status = {st: sum(1 for t in all_tasks if t.status == st) for st in VALID_STATUSES}
        critical_tasks = [t for t in all_tasks if t.is_critical_alert]
        return {
            "total": len(all_tasks),
            "by_status": by_status,
            "critical_pending_count": len(critical_tasks),
            "critical_task_ids": [t.id for t in critical_tasks],
            "critical_tasks": [
                {"id": t.id, "title": t.title, "reason": t.critical_reason} for t in critical_tasks
            ],
        }
