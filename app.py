from flask import Flask, render_template, request, redirect, url_for, jsonify
import json
import os
from datetime import datetime, date, timedelta
from supabase import create_client, Client
from zoneinfo import ZoneInfo

FUSO = ZoneInfo("America/Sao_Paulo") 

app = Flask(__name__)
@app.route("/health") 
def health(): 
    return "OK", 200 

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")

#SUPABASE_URL = "https://maxdqycohsopgeacpyoy.supabase.co"
#SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im1heGRxeWNvaHNvcGdlYWNweW95Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTE5ODY5MzEsImV4cCI6MjA2NzU2MjkzMX0.Noj3VmkV3zJ3iRlptetkIzL9g_-ZU4wx_gnhzLMFyMA"

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

REGIOES_ES = [
    "Grande Vitória",
    "Norte",
    "Noroeste",
    "Serrana",
    "Sul",
    "Sul / Caparaó",
]
STATUS_SERVICO = [
    "A confirmar",
    "Agendado",
    "Finalizado Bling",
    "Concluído",
    "Problema / Retorno necessário",
    "Rascunho",
]


def carregar_municipios():
    response = supabase.table("3_ata_regiao") \
        .select("municipio, regiao") \
        .order("municipio") \
        .execute()
    return response.data


def ler_colaboradores_form():
    colaboradores = [
        nome.strip()
        for nome in request.form.getlist("colaboradores")
        if nome.strip()
    ]
    if len(colaboradores) > 4:
        raise ValueError("É permitido informar no máximo 4 colaboradores.")
    return colaboradores


def carregar_catalogo_equipamentos():
    response = supabase.table("3_ata_equipamentos") \
        .select("id, categoria, equipamento, tipo, ferramentas") \
        .eq("ativo", True) \
        .order("categoria") \
        .order("equipamento") \
        .execute()
    return response.data


def carregar_categorias_equipamentos():
    response = supabase.table("3_ata_categorias_equipamentos") \
        .select("id, nome") \
        .order("nome") \
        .execute()
    return response.data


def ler_equipamentos_form(catalogo):
    try:
        enviados = json.loads(request.form.get("equipamentos_json", "[]"))
    except json.JSONDecodeError as erro:
        raise ValueError("Não foi possível ler os equipamentos informados.") from erro

    if not isinstance(enviados, list) or len(enviados) > 6:
        raise ValueError("É permitido adicionar no máximo 6 equipamentos.")

    por_id = {str(item["id"]): item for item in catalogo}
    equipamentos = []
    for enviado in enviados:
        if not isinstance(enviado, dict):
            raise ValueError("Um dos equipamentos informados é inválido.")

        catalogo_id = str(enviado.get("catalogo_id", ""))
        item_catalogo = por_id.get(catalogo_id)
        if not item_catalogo:
            raise ValueError("Selecione um equipamento válido do catálogo.")

        ferramentas_enviadas = enviado.get("ferramentas", [])
        if not isinstance(ferramentas_enviadas, list):
            raise ValueError("A lista de ferramentas de um equipamento é inválida.")
        ferramentas_por_nome = {
            item.get("nome", "").strip(): item.get("levado") is True
            for item in ferramentas_enviadas
            if isinstance(item, dict) and isinstance(item.get("nome"), str)
        }

        if item_catalogo["tipo"] == "Montagem":
            nomes_ferramentas = item_catalogo.get("ferramentas") or []
        else:
            nomes_ferramentas = [
                nome for nome in ferramentas_por_nome
                if nome
            ]

        ferramentas = []
        for nome in nomes_ferramentas:
            if not isinstance(nome, str) or not nome.strip():
                continue
            nome = nome.strip()
            ferramentas.append({
                "nome": nome,
                "levado": ferramentas_por_nome.get(nome, False),
            })

        equipamentos.append({
            "catalogo_id": item_catalogo["id"],
            "categoria": item_catalogo["categoria"],
            "equipamento": item_catalogo["equipamento"],
            "tipo": item_catalogo["tipo"],
            "levado": enviado.get("levado") is True,
            "ferramentas": ferramentas,
        })

    return equipamentos


@app.route("/equipamentos", methods=["GET", "POST"])
def gerenciar_equipamentos():
    categorias = carregar_categorias_equipamentos()
    catalogo = supabase.table("3_ata_equipamentos") \
        .select("id, categoria, equipamento, tipo, ferramentas, ativo") \
        .order("categoria") \
        .order("equipamento") \
        .execute().data

    def render_catalog(erro=None, mensagem=None, equipamento_id=None):
        selecionado = next(
            (
                item for item in catalogo
                if str(item["id"]) == str(equipamento_id)
            ),
            None,
        )
        return render_template(
            "equipamentos.html",
            categorias=categorias,
            catalogo=catalogo,
            equipamento_selecionado=selecionado,
            erro=erro,
            mensagem=mensagem,
        )

    if request.method == "GET":
        return render_catalog(
            mensagem=request.args.get("mensagem"),
            equipamento_id=request.args.get("equipamento_id"),
        )

    acao = request.form.get("acao", "")
    if acao == "criar_categoria":
        nome = request.form.get("categoria", "").strip()
        if not nome or len(nome) > 80:
            return render_catalog("Informe uma categoria com até 80 caracteres.")
        if any(item["nome"].casefold() == nome.casefold() for item in categorias):
            return render_catalog("Essa categoria já está cadastrada.")
        supabase.table("3_ata_categorias_equipamentos").insert({
            "nome": nome,
        }).execute()
        return redirect(url_for(
            "gerenciar_equipamentos",
            mensagem="Categoria cadastrada.",
        ))

    if acao == "criar_equipamento":
        categoria = request.form.get("categoria", "").strip()
        nome = request.form.get("equipamento", "").strip()
        categorias_existentes = {item["nome"] for item in categorias}
        if categoria not in categorias_existentes:
            return render_catalog("Selecione uma categoria válida.")
        if not nome or len(nome) > 120:
            return render_catalog("Informe um equipamento com até 120 caracteres.")
        if any(
            item["categoria"] == categoria
            and item["equipamento"].casefold() == nome.casefold()
            for item in catalogo
        ):
            return render_catalog("Esse equipamento já está cadastrado nessa categoria.")
        response = supabase.table("3_ata_equipamentos").insert({
            "categoria": categoria,
            "equipamento": nome,
            "tipo": "Montagem",
            "ferramentas": [],
            "ativo": True,
        }).select("id").execute()
        return redirect(url_for(
            "gerenciar_equipamentos",
            mensagem="Equipamento cadastrado.",
            equipamento_id=response.data[0]["id"],
        ))

    if acao in {"salvar_ferramentas", "copiar_ferramentas", "excluir_equipamento"}:
        equipamento_id = request.form.get("equipamento_id", "")
        equipamento = next(
            (item for item in catalogo if str(item["id"]) == equipamento_id),
            None,
        )
        if not equipamento:
            return render_catalog("Selecione um equipamento válido.")

        if acao == "salvar_ferramentas":
            ferramentas = [
                nome.strip()
                for nome in request.form.getlist("ferramentas")
                if nome.strip()
            ]
            if len(ferramentas) > 30:
                return render_catalog(
                    "É permitido cadastrar no máximo 30 ferramentas por equipamento.",
                    equipamento_id=equipamento_id,
                )
            if any(len(nome) > 120 for nome in ferramentas):
                return render_catalog(
                    "Cada ferramenta pode ter até 120 caracteres.",
                    equipamento_id=equipamento_id,
                )
            nomes_unicos = {nome.casefold() for nome in ferramentas}
            if len(nomes_unicos) != len(ferramentas):
                return render_catalog(
                    "Remova ferramentas repetidas antes de salvar.",
                    equipamento_id=equipamento_id,
                )
            supabase.table("3_ata_equipamentos").update({
                "ferramentas": ferramentas,
            }).eq("id", equipamento_id).execute()
            return redirect(url_for(
                "gerenciar_equipamentos",
                mensagem="Ferramentas salvas.",
                equipamento_id=equipamento_id,
            ))

        if acao == "copiar_ferramentas":
            origem_id = request.form.get("origem_id", "")
            origem = next(
                (item for item in catalogo if str(item["id"]) == origem_id),
                None,
            )
            if not origem or origem["id"] == equipamento["id"]:
                return render_catalog(
                    "Selecione outro equipamento como origem.",
                    equipamento_id=equipamento_id,
                )
            supabase.table("3_ata_equipamentos").update({
                "ferramentas": origem.get("ferramentas") or [],
            }).eq("id", equipamento_id).execute()
            return redirect(url_for(
                "gerenciar_equipamentos",
                mensagem=f"Ferramentas copiadas de {origem['equipamento']}.",
                equipamento_id=equipamento_id,
            ))

        supabase.table("3_ata_equipamentos") \
            .delete() \
            .eq("id", equipamento_id) \
            .execute()
        return redirect(url_for(
            "gerenciar_equipamentos",
            mensagem="Equipamento excluído.",
        ))

    return render_catalog("Ação inválida.")


@app.route("/lista-compras", methods=["GET", "POST"])
def lista_compras():
    erro = None
    item = ""
    observacao = ""

    if request.method == "POST":
        item = request.form.get("item", "").strip()
        observacao = request.form.get("observacao", "").strip()
        if not item or len(item) > 160:
            erro = "Informe o que precisa comprar (até 160 caracteres)."
        elif len(observacao) > 500:
            erro = "A observação pode ter até 500 caracteres."
        else:
            supabase.table("3_ata_lista_compras").insert({
                "item": item,
                "observacao": observacao or None,
                "criado_em": datetime.now().isoformat(timespec="seconds"),
            }).execute()
            return redirect(url_for(
                "lista_compras",
                mensagem="Item adicionado à lista.",
            ))

    resposta = supabase.table("3_ata_lista_compras") \
        .select("*") \
        .order("criado_em", desc=True) \
        .execute()
    compras = resposta.data or []
    for compra in compras:
        compra["data_formatada"] = datetime.fromisoformat(
            str(compra["criado_em"]).replace("Z", "+00:00")
        ).astimezone(FUSO).strftime("%d/%m/%Y - %H:%M")

    return render_template(
        "lista_compras.html",
        compras=compras,
        erro=erro,
        mensagem=request.args.get("mensagem"),
        item=item,
        observacao=observacao,
    )


@app.route("/lista-compras/<int:compra_id>/excluir", methods=["POST"])
def excluir_item_compra(compra_id):
    resposta = supabase.table("3_ata_lista_compras") \
        .delete() \
        .eq("id", compra_id) \
        .select("id") \
        .execute()
    if not resposta.data:
        return redirect(url_for(
            "lista_compras",
            mensagem="O item já foi removido ou não existe.",
        ))

    return redirect(url_for(
        "lista_compras",
        mensagem="Item removido da lista de compras.",
    ))


@app.route("/motorista", methods=["GET", "POST"])
def motorista():
    erro = None
    dados = {
        "data": request.form.get("data", hoje_local().isoformat()),
        "veiculo": request.form.get("veiculo", ""),
        "colaborador": request.form.get("colaborador", "").strip(),
        "observacao": request.form.get("observacao", "").strip(),
    }

    if request.method == "POST":
        try:
            date.fromisoformat(dados["data"])
        except ValueError:
            erro = "Selecione uma data válida."
        if not erro and dados["veiculo"] not in {"Fiorino", "Oroch", "Outro"}:
            erro = "Selecione um veículo válido."
        if not erro and (
            not dados["colaborador"] or len(dados["colaborador"]) > 120
        ):
            erro = "Informe o nome do colaborador (até 120 caracteres)."
        if not erro and len(dados["observacao"]) > 500:
            erro = "A observação pode ter até 500 caracteres."

        if not erro:
            supabase.table("3_ata_motoristas").insert({
                "data": dados["data"],
                "veiculo": dados["veiculo"],
                "colaborador": dados["colaborador"],
                "observacao": dados["observacao"] or None,
                "criado_em": datetime.now().isoformat(timespec="seconds"),
            }).execute()
            return redirect(url_for(
                "motorista",
                mensagem="Registro de motorista salvo.",
            ))

    resposta = supabase.table("3_ata_motoristas") \
        .select("*") \
        .order("data", desc=True) \
        .order("criado_em", desc=True) \
        .execute()
    registros = resposta.data or []
    for registro in registros:
        registro["data_formatada"] = date.fromisoformat(
            str(registro["data"])[:10]
        ).strftime("%d/%m/%Y")

    return render_template(
        "motorista.html",
        registros=registros,
        erro=erro,
        mensagem=request.args.get("mensagem"),
        dados=dados,
    )


def carregar_equipamentos_servico(servico_id):
    response = supabase.table("3_ata_servico_equipamentos") \
        .select("*") \
        .eq("servico_id", servico_id) \
        .order("ordem") \
        .execute()
    equipamentos = response.data
    ids = [item["id"] for item in equipamentos]
    if not ids:
        return []

    ferramentas_response = supabase.table("3_ata_servico_ferramentas") \
        .select("*") \
        .in_("servico_equipamento_id", ids) \
        .order("ordem") \
        .execute()
    ferramentas_por_equipamento = {}
    for ferramenta in ferramentas_response.data:
        ferramentas_por_equipamento.setdefault(
            ferramenta["servico_equipamento_id"], []
        ).append({
            "id": ferramenta["id"],
            "nome": ferramenta["ferramenta"],
            "levado": ferramenta["levado"],
        })

    for equipamento in equipamentos:
        equipamento["ferramentas"] = ferramentas_por_equipamento.get(
            equipamento["id"], []
        )
        equipamento["catalogo_id"] = equipamento["equipamento_id"]
    return equipamentos


def salvar_equipamentos_servico(servico_id, equipamentos):
    supabase.table("3_ata_servico_equipamentos") \
        .delete() \
        .eq("servico_id", servico_id) \
        .execute()

    for ordem, equipamento in enumerate(equipamentos, start=1):
        response = supabase.table("3_ata_servico_equipamentos").insert({
            "servico_id": servico_id,
            "equipamento_id": equipamento["catalogo_id"],
            "categoria": equipamento["categoria"],
            "equipamento": equipamento["equipamento"],
            "tipo": equipamento["tipo"],
            "levado": equipamento["levado"],
            "ordem": ordem,
        }).select("id").execute()
        servico_equipamento_id = response.data[0]["id"]
        ferramentas = [
            {
                "servico_equipamento_id": servico_equipamento_id,
                "ferramenta": ferramenta["nome"],
                "levado": ferramenta["levado"],
                "ordem": ordem_ferramenta,
            }
            for ordem_ferramenta, ferramenta in enumerate(
                equipamento["ferramentas"], start=1
            )
        ]
        if ferramentas:
            supabase.table("3_ata_servico_ferramentas") \
                .insert(ferramentas) \
                .execute()


def salvar_confirmacoes_equipamentos_servico(
    servico_id,
    equipamentos,
    equipamentos_confirmados,
    ferramentas_confirmadas,
):
    equipamentos_confirmados = {str(item) for item in equipamentos_confirmados}
    ferramentas_confirmadas = {str(item) for item in ferramentas_confirmadas}

    equipamentos_marcados = [
        str(item["id"]) for item in equipamentos
        if str(item["id"]) in equipamentos_confirmados
    ]
    equipamentos_desmarcados = [
        str(item["id"]) for item in equipamentos
        if str(item["id"]) not in equipamentos_confirmados
    ]
    ferramentas = [
        ferramenta
        for equipamento in equipamentos
        for ferramenta in equipamento["ferramentas"]
    ]
    ferramentas_marcadas = [
        str(item["id"]) for item in ferramentas
        if str(item["id"]) in ferramentas_confirmadas
    ]
    ferramentas_desmarcadas = [
        str(item["id"]) for item in ferramentas
        if str(item["id"]) not in ferramentas_confirmadas
    ]

    if equipamentos_marcados:
        supabase.table("3_ata_servico_equipamentos") \
            .update({"levado": True}) \
            .in_("id", equipamentos_marcados) \
            .eq("servico_id", servico_id) \
            .execute()
    if equipamentos_desmarcados:
        supabase.table("3_ata_servico_equipamentos") \
            .update({"levado": False}) \
            .in_("id", equipamentos_desmarcados) \
            .eq("servico_id", servico_id) \
            .execute()
    if ferramentas_marcadas:
        supabase.table("3_ata_servico_ferramentas") \
            .update({"levado": True}) \
            .in_("id", ferramentas_marcadas) \
            .execute()
    if ferramentas_desmarcadas:
        supabase.table("3_ata_servico_ferramentas") \
            .update({"levado": False}) \
            .in_("id", ferramentas_desmarcadas) \
            .execute()


def hoje_local():
    return datetime.now(FUSO).date()


@app.context_processor
def utility_processor():
    return {"today": hoje_local().isoformat()}


def carregar_resumo_servicos():
    linhas = []
    inicio = 0
    tamanho = 1000
    while True:
        resposta = supabase.table("3_ata_servicos") \
            .select("status, data_prevista, cidade") \
            .range(inicio, inicio + tamanho - 1) \
            .execute()
        bloco = resposta.data or []
        linhas.extend(bloco)
        if len(bloco) < tamanho:
            return linhas
        inicio += tamanho

@app.route("/")
def index():
    hoje = hoje_local()
    inicio_mes = hoje.replace(day=1)
    proximo_mes = (inicio_mes.replace(day=28) + timedelta(days=4)).replace(day=1)
    fim_mes = proximo_mes - timedelta(days=1)
    limite_4 = hoje + timedelta(days=4)
    limite_7 = hoje + timedelta(days=6)
    limite_9 = hoje + timedelta(days=9)
    limite_15 = hoje + timedelta(days=14)

    municipios = carregar_municipios()
    regiao_por_cidade = {item["municipio"]: item["regiao"] for item in municipios}
    regioes = {regiao: {"7D": 0, "15D": 0, "Mês": 0} for regiao in list(REGIOES_ES) + ["Total"]}

    agendados_hoje = agendados_proximos = 0
    confirmar_agendamento = completar_os = 0
    finalizado_bling_mes = atualizar_bling = 0

    for linha in carregar_resumo_servicos():
        status = linha.get("status")
        bruto = linha.get("data_prevista")
        try:
            dia = date.fromisoformat(str(bruto)[:10]) if bruto else None
        except ValueError:
            dia = None

        if status == "Rascunho":
            completar_os += 1
        if dia is None:
            continue

        if status == "Agendado" and hoje <= dia <= limite_4:
            agendados_proximos += 1
            if dia == hoje:
                agendados_hoje += 1
        if status == "A confirmar" and hoje <= dia <= limite_9:
            confirmar_agendamento += 1
        if inicio_mes <= dia <= fim_mes and status == "Finalizado Bling":
            finalizado_bling_mes += 1
        if inicio_mes <= dia <= fim_mes and status == "Concluído":
            atualizar_bling += 1
        if not status or status == "Finalizado Bling":
            continue

        regiao = regiao_por_cidade.get(linha.get("cidade"))
        if hoje <= dia <= limite_7:
            regioes["Total"]["7D"] += 1
            if regiao in regioes:
                regioes[regiao]["7D"] += 1
        if hoje <= dia <= limite_15:
            regioes["Total"]["15D"] += 1
            if regiao in regioes:
                regioes[regiao]["15D"] += 1
        if inicio_mes <= dia <= fim_mes:
            regioes["Total"]["Mês"] += 1
            if regiao in regioes:
                regioes[regiao]["Mês"] += 1

    return render_template(
        "index.html",
        agendados_hoje=agendados_hoje,
        agendados_proximos=agendados_proximos,
        confirmar_agendamento=confirmar_agendamento,
        completar_os=completar_os,
        finalizado_bling_mes=finalizado_bling_mes,
        atualizar_bling=atualizar_bling,
        regioes=regioes,
    )

@app.route("/servicos")
def servicos():
    response = supabase.table("3_ata_servicos") \
        .select("*") \
        .order("data_prevista", desc=False, nullsfirst=False) \
        .order("id", desc=True) \
        .execute()

    municipios = carregar_municipios()
    regioes_por_municipio = {item["municipio"]: item["regiao"] for item in municipios}
    rows = response.data
    for row in rows:
        row["regiao"] = regioes_por_municipio.get(row.get("cidade"), row.get("regiao", ""))

    return render_template(
        "servicos.html",
        servicos=rows,
        regioes=REGIOES_ES,
    )


@app.route("/servicos/novo", methods=["GET", "POST"])
def novo_servico():
    municipios = carregar_municipios()
    regioes_por_municipio = {item["municipio"]: item["regiao"] for item in municipios}
    catalogo_equipamentos = carregar_catalogo_equipamentos()

    def render_form(
        erro,
        equipamentos,
        cidade="",
        colaboradores=None,
        status_selecionado="A confirmar",
        tipo_selecionado="Montagem",
    ):
        return render_template(
            "novo_servico.html",
            erro=erro,
            municipios=municipios,
            cidade_selecionada=cidade,
            regiao_selecionada=regioes_por_municipio.get(cidade, ""),
            catalogo_equipamentos=catalogo_equipamentos,
            equipamentos=equipamentos,
            colaboradores=(colaboradores or [])[:4],
            status_selecionado=status_selecionado,
            status_opcoes=STATUS_SERVICO,
            tipo_selecionado=tipo_selecionado,
        )

    if request.method == "POST":
        tipo = request.form.get("tipo", "Assistência Técnica")
        cliente = request.form.get("cliente", "").strip()
        cidade = request.form.get("cidade", "").strip()
        status = request.form.get("status", "A confirmar")
        if tipo == "Rascunho":
            status = "Rascunho"
        try:
            colaboradores = ler_colaboradores_form()
            erro_colaboradores = None
        except ValueError as erro:
            colaboradores = [
                nome.strip()
                for nome in request.form.getlist("colaboradores")
                if nome.strip()
            ][:4]
            erro_colaboradores = str(erro)
        try:
            equipamentos = ler_equipamentos_form(catalogo_equipamentos)
            erro_equipamentos = None
        except ValueError as erro:
            equipamentos = []
            erro_equipamentos = str(erro)

        if tipo not in ["Montagem", "Assistência Técnica", "Garantia", "Rascunho"]:
            return render_form(
                "Tipo de serviço inválido.", equipamentos, cidade,
                colaboradores, status, tipo,
            )
        if tipo != "Rascunho" and status == "Rascunho":
            return render_form(
                "O status Rascunho só pode ser usado quando o tipo do serviço também for Rascunho.",
                equipamentos, cidade, colaboradores, "A confirmar", tipo,
            )
        if status not in STATUS_SERVICO:
            return render_form(
                "Status de serviço inválido.", equipamentos, cidade,
                colaboradores, status, tipo,
            )
        if status == "Agendado" and any(
            not equipamento["levado"]
            or any(not ferramenta["levado"] for ferramenta in equipamento["ferramentas"])
            for equipamento in equipamentos
        ):
            return render_form(
                "Confirme cada equipamento e ferramenta antes de agendar o serviço.",
                equipamentos, cidade, colaboradores, status, tipo,
            )
        if erro_colaboradores:
            return render_form(
                erro_colaboradores, equipamentos, cidade,
                colaboradores, status, tipo,
            )
        if erro_equipamentos:
            return render_form(
                erro_equipamentos, equipamentos, cidade,
                colaboradores, status, tipo,
            )

        telefone = request.form.get("telefone", "").strip()
        endereco = request.form.get("endereco", "").strip()
        data_prevista = request.form.get("data_prevista", "")
        observacoes = request.form.get("observacoes", "").strip()

        if not cliente:
            return render_form(
                "Informe o cliente/empresa.", equipamentos, cidade,
                colaboradores, status, tipo,
            )
        regiao = regioes_por_municipio.get(cidade)
        if not regiao:
            return render_form(
                "Selecione uma cidade válida da lista.", equipamentos, cidade,
                colaboradores, status, tipo,
            )

        cur = supabase.table("3_ata_servicos").insert({
            "tipo": tipo,
            "regiao": regiao,
            "cliente": cliente,
            "cidade": cidade,
            "telefone": telefone,
            "endereco": endereco,
            "data_prevista": data_prevista or None,
            "observacoes": observacoes,
            "colaboradores": colaboradores,
            "status": status,
            "criado_em": datetime.now().isoformat(timespec="seconds")
        }).execute()
        
        servico_id = cur.data[0]["id"]
        salvar_equipamentos_servico(servico_id, equipamentos)
        
        if observacoes:
            supabase.table("3_ata_historico").insert({
                "servico_id": servico_id,
                "texto": "Observação inicial: " + observacoes,
                "criado_em": datetime.now().isoformat(timespec="seconds")
            }).execute()
        if status == "Agendado":
            supabase.table("3_ata_historico").insert({
                "servico_id": servico_id,
                "texto": (
                    "Serviço criado como Agendado; todos os equipamentos e "
                    "ferramentas foram confirmados como separados "
                    "(responsável não identificado)."
                ),
                "criado_em": datetime.now().isoformat(timespec="seconds")
            }).execute()
        return redirect(url_for("detalhes", servico_id=servico_id))

    return render_form(None, [], status_selecionado="A confirmar")


@app.route("/servicos/<int:servico_id>/editar", methods=["GET", "POST"])
def editar_servico(servico_id):
    servico_response = supabase.table("3_ata_servicos") \
        .select("*") \
        .eq("id", servico_id) \
        .single() \
        .execute()

    servico = servico_response.data
    if not servico:
        return "Serviço não encontrado", 404

    erro = None
    data_prevista_input = str(servico.get("data_prevista") or "")[:10]
    municipios = carregar_municipios()
    regioes_por_municipio = {item["municipio"]: item["regiao"] for item in municipios}
    catalogo_equipamentos = carregar_catalogo_equipamentos()
    equipamentos = carregar_equipamentos_servico(servico_id)

    if request.method == "POST":
        dados = {
            "tipo": request.form.get("tipo", ""),
            "cliente": request.form.get("cliente", "").strip(),
            "cidade": request.form.get("cidade", "").strip(),
            "telefone": request.form.get("telefone", "").strip(),
            "endereco": request.form.get("endereco", "").strip(),
            "data_prevista": request.form.get("data_prevista", ""),
            "observacoes": request.form.get("observacoes", "").strip(),
        }
        try:
            dados["colaboradores"] = ler_colaboradores_form()
        except ValueError as erro_form:
            erro = str(erro_form)
            dados["colaboradores"] = [
                nome.strip()
                for nome in request.form.getlist("colaboradores")
                if nome.strip()
            ][:4]
        data_prevista_input = dados["data_prevista"]
        try:
            equipamentos = ler_equipamentos_form(catalogo_equipamentos)
        except ValueError as erro_form:
            erro = erro or str(erro_form)

        if erro:
            servico.update(dados)
        elif dados["tipo"] not in ["Montagem", "Assistência Técnica", "Garantia", "Rascunho"]:
            erro = "Tipo de serviço inválido."
            servico.update(dados)
        elif not dados["cliente"]:
            erro = "Informe o cliente/empresa."
            servico.update(dados)
        elif dados["cidade"] not in regioes_por_municipio:
            erro = "Selecione uma cidade válida da lista."
            servico.update(dados)
        else:
            dados["regiao"] = regioes_por_municipio[dados["cidade"]]
            if dados["tipo"] == "Rascunho":
                dados["status"] = "Rascunho"
            elif servico.get("tipo") == "Rascunho" or servico.get("status") == "Rascunho":
                dados["status"] = "A confirmar"
            dados["data_prevista"] = dados["data_prevista"] or None
            supabase.table("3_ata_servicos").update(dados).eq("id", servico_id).execute()
            salvar_equipamentos_servico(servico_id, equipamentos)
            return redirect(url_for("detalhes", servico_id=servico_id))

    return render_template(
        "editar_servico.html",
        servico=servico,
        data_prevista_input=data_prevista_input,
        municipios=municipios,
        regiao_selecionada=regioes_por_municipio.get(servico.get("cidade"), ""),
        catalogo_equipamentos=catalogo_equipamentos,
        equipamentos=equipamentos,
        colaboradores=(servico.get("colaboradores") or [])[:4],
        erro=erro,
    )


@app.route("/servicos/<int:servico_id>")
def detalhes(servico_id):
    servico_response = supabase.table("3_ata_servicos") \
        .select("*") \
        .eq("id", servico_id) \
        .single() \
        .execute()
    
    servico = servico_response.data
    municipio = next(
        (item for item in carregar_municipios() if item["municipio"] == servico.get("cidade")),
        None,
    ) if servico else None
    if municipio:
        servico["regiao"] = municipio["regiao"]
    
    historico_response = supabase.table("3_ata_historico") \
        .select("*") \
        .eq("servico_id", servico_id) \
        .order("criado_em", desc=True) \
        .execute()
    
    historico = historico_response.data

    if not servico:
        return "Serviço não encontrado", 404

    for item in historico:
        timestamp = str(item["criado_em"]).replace("Z", "+00:00")
        item["criado_em_formatado"] = datetime.fromisoformat(timestamp).strftime("%d/%m/%Y - %H:%M")

    data_prevista = servico.get("data_prevista")
    data_prevista_formatada = (
        datetime.strptime(str(data_prevista)[:10], "%Y-%m-%d").strftime("%d-%m-%Y")
        if data_prevista else None
    )
    criado_em = servico.get("criado_em")
    criado_em_formatado = (
        datetime.strptime(str(criado_em)[:10], "%Y-%m-%d").strftime("%d-%m-%Y")
        if criado_em else None
    )
    telefone = str(servico.get("telefone") or "")
    telefone_digitos = "".join(caractere for caractere in telefone if caractere.isdigit())
    telefone_whatsapp = (
        telefone_digitos if telefone_digitos.startswith("55") else f"55{telefone_digitos}"
    ) if telefone_digitos else ""

    return render_template(
        "detalhes.html",
        servico=servico,
        historico=historico,
        equipamentos=carregar_equipamentos_servico(servico_id),
        erro=request.args.get("erro"),
        data_prevista_formatada=data_prevista_formatada,
        criado_em_formatado=criado_em_formatado,
        telefone_whatsapp=telefone_whatsapp,
    )


@app.route("/servicos/<int:servico_id>/status", methods=["POST"])
def alterar_status(servico_id):
    status = request.form.get("status", "")
    permitidos = [
        "Rascunho",
        "A confirmar",
        "Agendado",
        "Finalizado Bling",
        "Concluído",
        "Problema / Retorno necessário",
    ]
    servico_response = supabase.table("3_ata_servicos") \
        .select("tipo, status") \
        .eq("id", servico_id) \
        .single() \
        .execute()
    servico = servico_response.data
    if not servico:
        return "Serviço não encontrado", 404

    if status not in permitidos:
        return redirect(url_for(
            "detalhes", servico_id=servico_id,
            erro="Status de serviço inválido.",
        ))
    if servico["tipo"] == "Rascunho":
        status = "Rascunho"
    elif status == "Rascunho":
        return redirect(url_for(
            "detalhes", servico_id=servico_id,
            erro="O status Rascunho só pode ser usado quando o tipo do serviço também for Rascunho.",
        ))
    equipamentos = carregar_equipamentos_servico(servico_id)
    equipamentos_confirmados = request.form.getlist("equipamento_confirmado")
    ferramentas_confirmadas = request.form.getlist("ferramenta_confirmada")
    todos_confirmados = (
        all(str(item["id"]) in equipamentos_confirmados for item in equipamentos)
        and all(
            str(ferramenta["id"]) in ferramentas_confirmadas
            for item in equipamentos
            for ferramenta in item["ferramentas"]
        )
    )
    if status == "Agendado" and not todos_confirmados:
        if servico.get("status") != "Agendado":
            salvar_confirmacoes_equipamentos_servico(
                servico_id,
                equipamentos,
                equipamentos_confirmados,
                ferramentas_confirmadas,
            )
        return redirect(url_for(
            "detalhes", servico_id=servico_id,
            erro="Marque todos os equipamentos e ferramentas antes de agendar.",
        ))

    salvar_confirmacoes_equipamentos_servico(
        servico_id,
        equipamentos,
        equipamentos_confirmados,
        ferramentas_confirmadas,
    )

    dados = {
        "status": status,
        "foto_servico": request.form.get("foto_servico") == "on",
        "assinatura_cliente": request.form.get("assinatura_cliente") == "on",
        "epi_utilizado": request.form.get("epi_utilizado") == "on",
    }

    finalizados = ["Concluído", "Finalizado Bling"]
    data_conclusao = datetime.now().isoformat(timespec="seconds") if status in finalizados else None
    dados["data_conclusao"] = data_conclusao
    
    supabase.table("3_ata_servicos").update(dados).eq("id", servico_id).execute()
    if status in finalizados or (
        status == "Agendado" and servico.get("status") != "Agendado"
    ):
        texto_historico = (
            "Serviço agendado; todos os equipamentos e ferramentas foram "
            "confirmados como separados (responsável não identificado)."
            if status == "Agendado"
            else f"Serviço marcado como {status.lower()}."
        )
        supabase.table("3_ata_historico").insert({
            "servico_id": servico_id,
            "texto": texto_historico,
            "criado_em": datetime.now().isoformat(timespec="seconds")
        }).execute()
    return redirect(url_for("detalhes", servico_id=servico_id))


@app.route("/servicos/<int:servico_id>/observacao", methods=["POST"])
def adicionar_observacao(servico_id):
    texto = request.form.get("texto", "").strip()

    if texto:
        supabase.table("3_ata_historico").insert({
            "servico_id": servico_id,
            "texto": texto,
            "criado_em": datetime.now().isoformat(timespec="seconds")
        }).execute()

    return redirect(url_for("detalhes", servico_id=servico_id))

@app.route("/servicos/<int:servico_id>/excluir", methods=["POST"])
def excluir_servico(servico_id):
    nome_confirmacao = request.form.get("nome_confirmacao", "").strip()

    servico_response = supabase.table("3_ata_servicos") \
        .select("cliente") \
        .eq("id", servico_id) \
        .single() \
        .execute()

    servico = servico_response.data

    if not servico:
        return "Serviço não encontrado", 404

    if nome_confirmacao != servico["cliente"]:
        return redirect(url_for("detalhes", servico_id=servico_id))

    supabase.table("3_ata_historico") \
        .delete() \
        .eq("servico_id", servico_id) \
        .execute()

    supabase.table("3_ata_servicos") \
        .delete() \
        .eq("id", servico_id) \
        .execute()

    return redirect(url_for("servicos"))

@app.route("/api/servicos")
def api_servicos():
    response = supabase.table("3_ata_servicos") \
        .select("*") \
        .order("data_prevista", desc=False) \
        .order("id", desc=True) \
        .execute()

    municipios = carregar_municipios()
    regioes_por_municipio = {item["municipio"]: item["regiao"] for item in municipios}
    rows = response.data
    for row in rows:
        row["regiao"] = regioes_por_municipio.get(row.get("cidade"), row.get("regiao", ""))
    return jsonify(rows)

#if __name__ == "__main__":
#    app.run(host="0.0.0.0", port=5000, debug=True)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000, debug=False) #
