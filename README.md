# Sistema de Controle de Serviços — Assistência Técnica

MVP baseado na especificação funcional enviada.

## O que já funciona

- Dashboard inicial
- Cadastro rápido de Montagem, Assistência Técnica, Garantia ou Rascunho
- Regiões e municípios carregados da tabela `3_ata_regiao` no Supabase
- Cadastro provisório com status "A confirmar"
- Agenda/lista de serviços
- Filtros por texto, tipo, região e status
- A agenda mostra todos os serviços por padrão, exceto os "Finalizado Bling"; esse status fica disponível ao selecioná-lo no filtro
- Tela de detalhes
- Alteração de status
- Registro de observações e histórico
- Conclusão do serviço
- O tipo "Rascunho" é salvo automaticamente com o status "Rascunho"
- Checklist visual
- SQLite, sem necessidade de configurar banco externo
- Interface responsiva para celular

## Rodar localmente

```bash
pip install -r requirements.txt
python app.py
```

Depois abra:

`http://localhost:5000`

## GitHub

O banco `servicos.db` é criado automaticamente na primeira execução e deve ficar fora do Git.

Sugestão de `.gitignore`:

```text
__pycache__/
*.pyc
servicos.db
.venv/
venv/
.env
```

## Atualizações do Supabase

Para permitir o status "Finalizado Bling", execute o SQL de
[`20261009100400_rename_finalizado_bling_status.sql`](./supabase/migrations/20261009100400_rename_finalizado_bling_status.sql)
no SQL Editor do projeto Supabase. A alteração da constraint não é aplicada
automaticamente pela aplicação.

Para salvar os itens do checklist de conclusão, execute também
[`20261009101700_add_service_checklist.sql`](./supabase/migrations/20261009101700_add_service_checklist.sql)
no SQL Editor do projeto Supabase. A aplicação salva as marcações junto com o
status pelo botão “Salvar alterações”.

Para permitir o status "Rascunho", execute também
[`20261009103500_add_rascunho_status.sql`](./supabase/migrations/20261009103500_add_rascunho_status.sql)
no SQL Editor do projeto Supabase.

Para adicionar o campo opcional de cidade aos serviços, execute
[`20261009113400_add_city_to_services.sql`](./supabase/migrations/20261009113400_add_city_to_services.sql)
no SQL Editor do projeto Supabase.

## Próximas evoluções

1. Login/usuários
2. Upload de fotos
3. Assinatura digital na tela
4. Checklist persistente no banco
5. Integração com Google Maps/Waze
6. Calendário semanal
7. Roteirização por região
8. Equipamentos e peças
9. Relatórios
10. Deploy em Render, Railway ou VPS
