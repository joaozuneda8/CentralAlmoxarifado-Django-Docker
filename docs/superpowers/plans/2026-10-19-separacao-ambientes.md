# Separação de desenvolvimento e produção

Plano aprovado na conversa de 19/10/2026; execução nesta sessão.

Objetivo: separar Git, imagens, volumes e comandos de deploy no Docker Desktop
compartilhado do Windows 10 Pro, sem reiniciar Windows, WSL ou Docker e sem alterar GIS.

- [x] Testar as recusas do script PowerShell antes de implementar: alvo, branch, checkout,
  tag de produção, segredos de desenvolvimento e imagem divergente.
- [x] Acrescentar Compose explícito para os novos ambientes, preservando o Compose legado.
  Desenvolvimento será um projeto novo; o projeto antigo só poderá ser convertido após
  a virada, mediante roteiro separado (não reutilizar seus volumes por acidente).
- [x] Implementar planejamento por padrão, aplicação explícita e promoção por tag + digest.
  Não executar git pull/checkout, desligamentos ou limpeza dentro do atualizador.
- [x] Bloquear o atualizador legado e substituir seus testes antigos por testes de recusa.
- [x] Adicionar CI com MariaDB descartável e teste PowerShell; publicação manual no GHCR
  sem acesso ao servidor, com revisão do commit e teste antes de publicar.
- [x] Documentar Git, migração, HTTPS pendente, validação, backup e limites de rollback.
- [x] Verificar Compose resolvido, testes de deploy, lint e suíte existente; revisar a branch.
- [x] Criar develop e PR, configurar proteções compatíveis sem fazer merge ou deploy.

Decisões de execução:

- Trabalho na branch codex/separacao-ambientes do checkout limpo autorizado. Nenhuma alteração
  na máquina do André. Os testes usam processos simulados no limite do Docker e Git local
  temporário; não devem conectar ao SCPI nem a bancos de produção.
- Publicação inicial e ativação das integrações são etapas distintas; os scripts não fazem
  a migração final nem a troca da regra do MikroTik.
- O PowerShell 5.1 é o alvo Windows; CI deve testar também esse interpretador.

Revisão: colisão de projeto/volumes/imagens; resolução de caminhos em pastas com espaços;
variáveis herdadas do terminal; checks de tag desatualizados; migrations sem rollback automático.

Verificação local: 1292 testes aprovados, 1 ignorado (flags Windows); Ruff e migrations
sem diferenças; contratos PowerShell 7.6.7 e Compose 2.30.3 aprovados. CI Windows 5.1
a conferir no PR. Revisão independente sem achados materiais; barreira adicional
para agendador ativo coberta por teste de recusa observado falhar antes da correção.
GitHub: develop criada de bf2d0a6; main/develop protegidas com PR e checks;
ruleset de tags v* ativo. Nenhuma imagem publicada e nenhum deploy executado.
