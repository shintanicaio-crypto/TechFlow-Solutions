"""Aplicação web básica (Flask) com persistência SQLite e alertas de SLA crítico."""

import os
from flask import Flask, jsonify, redirect, render_template_string, request, url_for

from src.task_manager import (
    CRITICAL_SLA_THRESHOLD_HOURS,
    TaskManager,
    VALID_PRIORITIES,
    VALID_STATUSES,
)


def create_app(db_path: str | None = None, seed_examples: bool = True) -> Flask:
    """Factory da aplicação Flask para facilitar execução real e testes isolados."""
    app = Flask(__name__)
    resolved_db = db_path or os.getenv("TECHFLOW_DB_PATH", "data/techflow_tasks.db")
    manager = TaskManager(db_path=resolved_db)

    if seed_examples:
        manager.seed_once()

    app.config["TASK_MANAGER"] = manager

    @app.route("/", methods=["GET"])
    def index():
        """Renderiza o painel principal de tarefas."""
        error = request.args.get("error")
        return render_template_string(
            HTML_TEMPLATE,
            tasks=manager.list_tasks(),
            metrics=manager.get_metrics(),
            priorities=VALID_PRIORITIES,
            statuses=VALID_STATUSES,
            sla_threshold=CRITICAL_SLA_THRESHOLD_HOURS,
            error=error,
        )

    @app.route("/tasks", methods=["POST"])
    def create_task_route():
        """Cria uma nova tarefa a partir do formulário web."""
        try:
            sla_raw = request.form.get("sla_hours", "24")
            sla_hours = int(sla_raw)
            manager.create_task(
                title=request.form.get("title", ""),
                description=request.form.get("description", ""),
                status=request.form.get("status", "A Fazer"),
                priority=request.form.get("priority", "Média"),
                assignee=request.form.get("assignee", "Não atribuído"),
                logistics_hub=request.form.get("logistics_hub", "Hub Central"),
                sla_hours=sla_hours,
            )
            return redirect(url_for("index"))
        except (ValueError, KeyError) as exc:
            return redirect(url_for("index", error=str(exc)))

    @app.route("/tasks/<int:task_id>/advance", methods=["POST"])
    def advance_status_route(task_id: int):
        """Avança o status da tarefa no fluxo (A Fazer -> Em Progresso -> Concluído)."""
        order = {"A Fazer": "Em Progresso", "Em Progresso": "Concluído", "Concluído": "Concluído"}
        try:
            task = manager.get_task(task_id)
            manager.update_task(task_id, status=order[task.status])
        except KeyError as exc:
            return redirect(url_for("index", error=str(exc)))
        return redirect(url_for("index"))

    @app.route("/tasks/<int:task_id>/delete", methods=["POST"])
    def delete_task_route(task_id: int):
        """Remove permanentemente uma tarefa do banco de dados."""
        try:
            manager.delete_task(task_id)
        except KeyError as exc:
            return redirect(url_for("index", error=str(exc)))
        return redirect(url_for("index"))

    @app.route("/api/tasks", methods=["GET"])
    def api_list_tasks():
        """Endpoint JSON com tarefas persistidas e métricas."""
        tasks = [
            t.__dict__
            | {
                "is_critical_alert": t.is_critical_alert,
                "critical_reason": t.critical_reason,
            }
            for t in manager.list_tasks()
        ]
        return jsonify({"tasks": tasks, "metrics": manager.get_metrics()})

    return app


HTML_TEMPLATE = """
<!doctype html>
<html lang="pt-br">
<head>
  <meta charset="utf-8">
  <title>TechFlow Solutions — Gestão de Tarefas Logísticas</title>
  <style>
    body { font-family: Arial, sans-serif; margin: 2rem; background: #f5f7fa; color: #1f2937; }
    h1 { margin-bottom: 0.25rem; }
    .subtitle { color: #4b5563; margin-bottom: 1.5rem; }
    .metrics { display: flex; gap: 1rem; margin-bottom: 1.5rem; flex-wrap: wrap; }
    .card { background: #fff; border-radius: 8px; padding: 1rem; box-shadow: 0 1px 3px rgba(0,0,0,0.08); min-width: 140px; }
    .metric-val { font-size: 1.5rem; font-weight: bold; color: #1d4ed8; }
    .alert { color: #b91c1c; }
    .alert-banner { background: #fef2f2; border-left: 4px solid #dc2626; color: #7f1d1d; padding: 0.9rem 1rem; border-radius: 6px; margin-bottom: 1.5rem; }
    .alert-banner ul { margin: 0.4rem 0 0 1.2rem; padding: 0; }
    form { display: flex; gap: 0.5rem; flex-wrap: wrap; margin-bottom: 1.5rem; background: #fff; padding: 1rem; border-radius: 8px; }
    input, select, button { padding: 0.5rem; border: 1px solid #d1d5db; border-radius: 6px; }
    button { background: #1d4ed8; color: #fff; border: none; cursor: pointer; font-weight: bold; }
    button.danger { background: #dc2626; }
    table { width: 100%; border-collapse: collapse; background: #fff; border-radius: 8px; overflow: hidden; }
    th, td { padding: 0.75rem; border-bottom: 1px solid #e5e7eb; text-align: left; font-size: 0.92rem; }
    th { background: #eff6ff; }
    .badge-crit { background: #fee2e2; color: #991b1b; padding: 0.2rem 0.5rem; border-radius: 4px; font-weight: bold; font-size: 0.8rem; }
    .msg { background: #fef2f2; color: #991b1b; padding: 0.75rem; border-radius: 6px; margin-bottom: 1rem; }
    .empty { text-align: center; color: #6b7280; padding: 2rem; }
  </style>
</head>
<body>
  <h1>TechFlow Solutions</h1>
  <div class="subtitle">Sistema Ágil de Gerenciamento de Tarefas — Persistência SQLite</div>

  {% if error %}
  <div class="msg">{{ error }}</div>
  {% endif %}

  {% if metrics.critical_pending_count > 0 %}
  <div class="alert-banner">
    <strong>Notificação de Atenção Imediata ({{ metrics.critical_pending_count }}):</strong>
    Tarefas não concluídas com Prioridade Crítica ou SLA &le; {{ sla_threshold }}h:
    <ul>
      {% for item in metrics.critical_tasks %}
      <li><strong>#{{ item.id }} {{ item.title }}</strong> — {{ item.reason }}</li>
      {% endfor %}
    </ul>
  </div>
  {% endif %}

  <div class="metrics">
    <div class="card"><div>Total de Tarefas</div><div class="metric-val">{{ metrics.total }}</div></div>
    <div class="card"><div>A Fazer</div><div class="metric-val">{{ metrics.by_status["A Fazer"] }}</div></div>
    <div class="card"><div>Em Progresso</div><div class="metric-val">{{ metrics.by_status["Em Progresso"] }}</div></div>
    <div class="card"><div>Concluído</div><div class="metric-val">{{ metrics.by_status["Concluído"] }}</div></div>
    <div class="card"><div>Alertas Críticos</div><div class="metric-val alert">{{ metrics.critical_pending_count }}</div></div>
  </div>

  <form method="post" action="{{ url_for('create_task_route') }}">
    <input type="text" name="title" placeholder="Título da tarefa*" required>
    <input type="text" name="description" placeholder="Descrição">
    <input type="text" name="assignee" placeholder="Responsável">
    <input type="text" name="logistics_hub" placeholder="Hub Logístico" value="Hub Central">
    <input type="number" name="sla_hours" min="1" value="24" style="width: 95px;" title="SLA em horas (<= {{ sla_threshold }}h dispara alerta)">
    <select name="priority">
      {% for p in priorities %}<option value="{{ p }}">{{ p }}</option>{% endfor %}
    </select>
    <select name="status">
      {% for s in statuses %}<option value="{{ s }}">{{ s }}</option>{% endfor %}
    </select>
    <button type="submit">Adicionar Tarefa</button>
  </form>

  <table>
    <thead>
      <tr>
        <th>ID</th><th>Tarefa</th><th>Hub</th><th>SLA</th><th>Prioridade</th><th>Status</th><th>Responsável</th><th>Ações</th>
      </tr>
    </thead>
    <tbody>
      {% if tasks|length == 0 %}
      <tr>
        <td colspan="8" class="empty">Nenhuma tarefa cadastrada no banco de dados. Adicione uma nova acima.</td>
      </tr>
      {% endif %}
      {% for t in tasks %}
      <tr>
        <td>#{{ t.id }}</td>
        <td>
          <strong>{{ t.title }}</strong>
          {% if t.is_critical_alert %}<span class="badge-crit" title="{{ t.critical_reason }}">ALERTA: {{ t.critical_reason }}</span>{% endif %}
          {% if t.description %}<div style="color:#6b7280;font-size:0.82rem;">{{ t.description }}</div>{% endif %}
        </td>
        <td>{{ t.logistics_hub }}</td>
        <td>{{ t.sla_hours }}h</td>
        <td>{{ t.priority }}</td>
        <td>{{ t.status }}</td>
        <td>{{ t.assignee }}</td>
        <td>
          {% if t.status != "Concluído" %}
          <form method="post" action="{{ url_for('advance_status_route', task_id=t.id) }}" style="display:inline;background:none;padding:0;margin:0;">
            <button type="submit">Avançar Status</button>
          </form>
          {% endif %}
          <form method="post" action="{{ url_for('delete_task_route', task_id=t.id) }}" style="display:inline;background:none;padding:0;margin:0;">
            <button type="submit" class="danger">Excluir</button>
          </form>
        </td>
      </tr>
      {% endfor %}
    </tbody>
  </table>
</body>
</html>
"""


app = create_app()

if __name__ == "__main__":
    app.run(debug=True, port=5000)
