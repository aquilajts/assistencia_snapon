# Sistema de Controle de Serviços — Assistência Técnica

MVP baseado na especificação funcional enviada.

## O que já funciona

- Dashboard inicial
- Cadastro rápido de Montagem ou Assistência Técnica
- Regiões Norte, Sul e Grande Vitória
- Cadastro provisório com status "A confirmar"
- Agenda/lista de serviços
- Filtros por texto, tipo, região e status
- Tela de detalhes
- Alteração de status
- Registro de observações e histórico
- Conclusão do serviço
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
