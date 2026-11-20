"""Testes unitários e de persistência SQLite para o sistema TechFlow Solutions."""

import pytest

from src.app import create_app
from src.task_manager import TaskManager


def test_create_and_persist_task(tmp_path):
    """Verifica criação válida e persistência real no banco SQLite entre instâncias."""
    db_file = str(tmp_path / "test_tasks.db")
    manager1 = TaskManager(db_path=db_file)
    task = manager1.create_task(
        title="Separar pedidos urgentes",
        description="Priorizar cargas perecíveis",
        priority="Alta",
        assignee="Lucas",
        logistics_hub="CD Cajamar",
        sla_hours=8,
    )
    manager1.close()

    # Reabre o banco em nova instância para garantir que os dados persistiram
    manager2 = TaskManager(db_path=db_file)
    loaded = manager2.get_task(task.id)
    assert loaded.title == "Separar pedidos urgentes"
    assert loaded.logistics_hub == "CD Cajamar"
    assert loaded.sla_hours == 8
    manager2.close()


def test_delete_all_tasks_does_not_reseed(tmp_path):
    """Garante que após excluir todas as tarefas iniciais, elas não reaparecem."""
    db_file = str(tmp_path / "seed_once.db")
    app = create_app(db_path=db_file, seed_examples=True)
    client = app.test_client()
    manager: TaskManager = app.config["TASK_MANAGER"]

    initial_tasks = manager.list_tasks()
    assert len(initial_tasks) == 3

    for task in initial_tasks:
        resp = client.post(f"/tasks/{task.id}/delete", follow_redirects=True)
        assert resp.status_code == 200

    # Recarrega a página inicial e verifica que continua vazia
    home = client.get("/")
    assert home.status_code == 200
    assert manager.list_tasks() == []
    assert "Nenhuma tarefa cadastrada" in home.get_data(as_text=True)
    manager.close()


def test_create_task_invalid_title_raises_error():
    """Valida entrada: título vazio ou com apenas espaços deve falhar."""
    manager = TaskManager(db_path=":memory:")
    with pytest.raises(ValueError, match="título"):
        manager.create_task(title="   ")
    manager.close()


def test_create_task_invalid_sla_raises_error():
    """Valida entrada: SLA menor ou igual a zero deve gerar ValueError."""
    manager = TaskManager(db_path=":memory:")
    with pytest.raises(ValueError, match="SLA"):
        manager.create_task(title="Roteirizar frota", sla_hours=0)
    manager.close()


def test_critical_alert_logic_and_concluded_clearing():
    """Verifica motivo do alerta crítico e desativação automática ao concluir a tarefa."""
    manager = TaskManager(db_path=":memory:")
    t_sla = manager.create_task(title="Carga SLA 2h", priority="Média", sla_hours=2)
    t_crit = manager.create_task(title="Carga Crítica 12h", priority="Crítica", sla_hours=12)
    t_normal = manager.create_task(title="Carga normal", priority="Baixa", sla_hours=48)

    assert t_sla.is_critical_alert is True
    assert "SLA <= 4h" in t_sla.critical_reason
    assert t_crit.is_critical_alert is True
    assert "Prioridade Crítica" in t_crit.critical_reason
    assert t_normal.is_critical_alert is False

    metrics = manager.get_metrics()
    assert metrics["critical_pending_count"] == 2

    # Ao concluir uma tarefa crítica, o alerta dela deve sumir automaticamente
    updated = manager.update_task(t_sla.id, status="Concluído")
    assert updated.is_critical_alert is False
    assert updated.critical_reason == ""
    assert manager.get_metrics()["critical_pending_count"] == 1
    manager.close()
