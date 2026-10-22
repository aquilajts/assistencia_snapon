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
- Lista de compras com observação opcional por item e histórico dos registros
- Registro de motorista por dia, veículo e colaborador, com histórico e lembrete de segurança
- Cada equipamento e ferramenta possui confirmação individual e há uma opção para marcar todos. O serviço só pode ser agendado quando todos os itens estiverem confirmados; a confirmação fica registrada no histórico. Como o sistema não possui login, o histórico não identifica nominalmente quem confirmou.
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

Para que o formulário carregue as cidades com a chave pública do Supabase,
execute também
[`20261014084200_allow_public_read_regioes.sql`](./supabase/migrations/20261014084200_allow_public_read_regioes.sql)
no SQL Editor. Essa política permite somente leitura da tabela
`3_ata_regiao`; ela não permite cadastrar ou editar regiões pela aplicação.

Para criar as tabelas do catálogo e salvar equipamentos/ferramentas em cada
serviço, execute
[`20261014091500_add_equipment_tracking.sql`](./supabase/migrations/20261014091500_add_equipment_tracking.sql)
no SQL Editor. A carga inicial das categorias e equipamentos é feita pela
migração de gerenciamento logo abaixo.

Para habilitar o gerenciamento do catálogo pelo botão “Categorias e
equipamentos” no início, execute
[`20261014134500_manage_equipment_catalog.sql`](./supabase/migrations/20261014134500_manage_equipment_catalog.sql)
no SQL Editor. A migração cria as categorias e equipamentos desta lista como
Montagem, sem ferramentas cadastradas inicialmente. Depois, use a tela do
catálogo para manter até 30 ferramentas por equipamento, copiá-las de outro
equipamento ou removê-las individualmente.

Para salvar os colaboradores que atenderão cada serviço, execute
[`20261014130000_add_service_collaborators.sql`](./supabase/migrations/20261014130000_add_service_collaborators.sql)
no SQL Editor. A coluna aceita até quatro nomes por serviço.

Para registrar também a confirmação individual de cada equipamento, execute
[`20261022101500_add_equipment_confirmation.sql`](./supabase/migrations/20261022101500_add_equipment_confirmation.sql)
no SQL Editor do Supabase antes de atualizar a aplicação.

Para habilitar a lista de compras e o histórico de motoristas, execute
[`20261022113000_add_purchase_list_and_driver_logs.sql`](./supabase/migrations/20261022113000_add_purchase_list_and_driver_logs.sql)
no SQL Editor do Supabase antes de usar as novas telas.

Para permitir a exclusão dos itens comprados da lista, execute também
[`20261022114500_allow_purchase_list_delete.sql`](./supabase/migrations/20261022114500_allow_purchase_list_delete.sql)
no SQL Editor do Supabase.

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
