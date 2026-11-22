[README.md](https://github.com/user-attachments/files/35165386/README.md)
# TechFlow Solutions — Sistema Ágil de Gerenciamento de Tarefas Logísticas

Projeto desenvolvido para simular a atuação da **TechFlow Solutions** no desenvolvimento de um sistema de gerenciamento de tarefas baseado em metodologias ágeis para uma *startup* de logística, acompanhando o fluxo em tempo real, priorizando tarefas críticas e apoiando o monitoramento da equipe.

## Objetivo e Escopo Inicial
* **Objetivo:** Fornecer um sistema funcional de gerenciamento de tarefas operacionais (criar, listar, atualizar, excluir e consultar métricas) com persistência em banco de dados, validação de entradas, testes automatizados e integração contínua.
* **Escopo Inicial:** CRUD de tarefas com banco **SQLite** (`data/techflow_tasks.db`), acompanhamento de estados do fluxo (*A Fazer*, *Em Progresso*, *Concluído*), níveis de prioridade e suíte de testes automatizados com `pytest` via GitHub Actions.

## Metodologia Ágil Adotada
* **Abordagem:** **Kanban** (com entregas incrementais) aplicado via **GitHub Projects**, organizando o trabalho em colunas de fluxo (*A Fazer*, *Em Progresso* e *Concluído*) para visualizar gargalos e manter transparência sobre o andamento das entregas.

## Gestão de Mudança de Escopo
* **Alteração realizada:** Inclusão dos campos `logistics_hub` (unidade logística) e `sla_hours` (prazo em horas), além do sistema de notificação de **Alerta Crítico** (`is_critical_alert` e `critical_reason`), que destaca no painel superior e na tabela toda tarefa **não concluída** com prioridade `Crítica` ou `sla_hours <= 4`.
* **Justificativa:** Na operação logística, janelas curtas de entrega ou ocorrências críticas exigem visibilidade imediata da equipe antes do estouro do SLA, limpando o alerta automaticamente assim que a tarefa é concluída.

## Estrutura do Repositório
```text
├── .github/workflows/ci.yml      # Pipeline de integração contínua (Pytest)
├── src/
│   ├── __init__.py
│   ├── app.py                    # Interface web Flask + endpoint JSON /api/tasks
│   └── task_manager.py           # Persistência SQLite, regras de SLA crítico e CRUD
├── tests/
│   └── test_task_manager.py      # Testes unitários e de persistência SQLite
├── .gitignore
└── requirements.txt
```

## Como Executar o Projeto

1.**entre na pastacorreta**
```bash
   cd techflow_task_manager_Final
   ```

2. **Crie e ative um ambiente virtual:**
   ```bash
   python -m venv .venv
   # Linux/macOS:
   source .venv/bin/activate
   # Windows (PowerShell):
   .venv\Scripts\Activate.ps1
   ```

3. **Instale as dependências:**
   ```bash
   python -m pip install -r requirements.txt
   ```

4. **Execute os testes automatizados:**
   ```bash
   python -m pytest -v
   ```

5. **Execute a aplicação web:**
   ```bash
   python -m src.app
   ```
   Acesse `http://127.0.0.1:5000` no navegador. Os dados são salvos automaticamente em `data/techflow_tasks.db`.
