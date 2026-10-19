# Limites da análise semântica (Pyright + Django)

- O Pyright lê a `.venv` do projeto pelo `[tool.pyright]` do `pyproject.toml`; o `django-stubs` não está instalado.
- Por isso o Pyright aponta falsos erros em código Django correto: `Cannot access attribute "objects"` em modelos, `transaction.atomic` usado em `with` e outros acessos a atributos de modelos (na medição de 19/10/2026, 622 `reportAttributeAccessIssue` no projeto). Não corrigir o código por causa desses avisos.
- O LSP não enxerga o que passa por nome ou texto: `{% url %}` e templates `.html`, rotas por `reverse`, `apps.get_model` e os campos escondidos dos formulários HTMX. Para isso use `fs.search_for_pattern`.
- Migrations ficam em `*/migrations/`; não editar à mão (ver regra de migrations no `CLAUDE.md`).
- Mudou o `[tool.pyright]`? O servidor MCP do Serena precisa ser reiniciado (`/mcp` → reconectar): o Pyright em execução não relê a configuração.
