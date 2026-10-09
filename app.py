from flask import Flask, render_template, request, redirect, url_for, jsonify
import os
from datetime import datetime, date, timedelta
from supabase import create_client, Client

app = Flask(__name__)

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


def carregar_municipios():
    response = supabase.table("3_ata_regiao") \
        .select("municipio, regiao") \
        .order("municipio") \
        .execute()
    return response.data


@app.context_processor
def utility_processor():
    return {"today": date.today().isoformat()}


@app.route("/")
def index():
    hoje = date.today()
    inicio_mes = hoje.replace(day=1)
    proximo_mes = (inicio_mes.replace(day=28) + timedelta(days=4)).replace(day=1)
    fim_mes = proximo_mes - timedelta(days=1)

    def contar_status(status, data_inicio=None, data_fim=None):
        consulta = supabase.table("3_ata_servicos") \
            .select("id", count="exact") \
            .eq("status", status)
        if data_inicio:
            consulta = consulta.gte("data_prevista", data_inicio.isoformat())
        if data_fim:
            consulta = consulta.lte("data_prevista", data_fim.isoformat())
        return consulta.execute().count or 0

    agendados_hoje = contar_status("Agendado", hoje, hoje)
    agendados_proximos = contar_status("Agendado", hoje, hoje + timedelta(days=4))
    confirmar_agendamento = contar_status("A confirmar", hoje, hoje + timedelta(days=9))
    completar_os = contar_status("Rascunho")
    finalizado_bling_mes = contar_status("Finalizado Bling", inicio_mes, fim_mes)
    atualizar_bling = contar_status("Concluído", inicio_mes, fim_mes)

    municipios = carregar_municipios()
    cidades_por_regiao = {
        regiao: [item["municipio"] for item in municipios if item["regiao"] == regiao]
        for regiao in REGIOES_ES
    }

    regioes = {}
    for regiao, cidades in cidades_por_regiao.items():
        if not cidades:
            regioes[regiao] = {"7D": 0, "15D": 0, "Mês": 0}
            continue

        def contar_regiao(data_inicio, data_fim):
            return supabase.table("3_ata_servicos") \
                .select("id", count="exact") \
                .in_("cidade", cidades) \
                .gte("data_prevista", data_inicio.isoformat()) \
                .lte("data_prevista", data_fim.isoformat()) \
                .neq("status", "Finalizado Bling") \
                .execute().count or 0

        regioes[regiao] = {
            "7D": contar_regiao(hoje, hoje + timedelta(days=6)),
            "15D": contar_regiao(hoje, hoje + timedelta(days=14)),
            "Mês": contar_regiao(inicio_mes, fim_mes),
        }

    return render_template(
        "index.html",
        agendados_hoje=agendados_hoje,
        agendados_proximos=agendados_proximos,
        confirmar_agendamento=confirmar_agendamento,
        completar_os=completar_os,
        finalizado_bling_mes=finalizado_bling_mes,
        atualizar_bling=atualizar_bling,
        regioes=regioes
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
    if request.method == "POST":
        tipo = request.form.get("tipo", "Assistência Técnica")
        cliente = request.form.get("cliente", "").strip()
        cidade = request.form.get("cidade", "").strip()
        if tipo not in ["Montagem", "Assistência Técnica", "Garantia", "Rascunho"]:
            return render_template(
                "novo_servico.html",
                erro="Tipo de serviço inválido.",
                municipios=municipios,
                cidade_selecionada=cidade,
                regiao_selecionada=regioes_por_municipio.get(cidade, ""),
            )
        telefone = request.form.get("telefone", "").strip()
        endereco = request.form.get("endereco", "").strip()
        data_prevista = request.form.get("data_prevista", "")
        observacoes = request.form.get("observacoes", "").strip()
        status = "Rascunho" if tipo == "Rascunho" else "A confirmar"

        if not cliente:
            return render_template(
                "novo_servico.html",
                erro="Informe o cliente/empresa.",
                municipios=municipios,
                cidade_selecionada=cidade,
                regiao_selecionada=regioes_por_municipio.get(cidade, ""),
            )
        regiao = regioes_por_municipio.get(cidade)
        if not regiao:
            return render_template(
                "novo_servico.html",
                erro="Selecione uma cidade válida da lista.",
                municipios=municipios,
                cidade_selecionada=cidade,
                regiao_selecionada="",
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
            "status": status,
            "criado_em": datetime.now().isoformat(timespec="seconds")
        }).execute()
        
        servico_id = cur.data[0]["id"]
        
        if observacoes:
            supabase.table("3_ata_historico").insert({
                "servico_id": servico_id,
                "texto": "Observação inicial: " + observacoes,
                "criado_em": datetime.now().isoformat(timespec="seconds")
            }).execute()
        return redirect(url_for("detalhes", servico_id=servico_id))

    return render_template(
        "novo_servico.html",
        erro=None,
        municipios=municipios,
        cidade_selecionada="",
        regiao_selecionada="",
    )


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
        data_prevista_input = dados["data_prevista"]

        if dados["tipo"] not in ["Montagem", "Assistência Técnica", "Garantia", "Rascunho"]:
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
            return redirect(url_for("detalhes", servico_id=servico_id))

    return render_template(
        "editar_servico.html",
        servico=servico,
        data_prevista_input=data_prevista_input,
        municipios=municipios,
        regiao_selecionada=regioes_por_municipio.get(servico.get("cidade"), ""),
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
        data_prevista_formatada=data_prevista_formatada,
        criado_em_formatado=criado_em_formatado,
        telefone_whatsapp=telefone_whatsapp,
    )


@app.route("/servicos/<int:servico_id>/status", methods=["POST"])
def alterar_status(servico_id):
    status = request.form.get("status", "")
    permitidos = ["Rascunho", "A confirmar", "Agendado", "Finalizado Bling", "Concluído", "Problema / Retorno necessário"]
    if status not in permitidos:
        return redirect(url_for("detalhes", servico_id=servico_id))

    servico_response = supabase.table("3_ata_servicos") \
        .select("tipo") \
        .eq("id", servico_id) \
        .single() \
        .execute()
    servico = servico_response.data
    if not servico:
        return "Serviço não encontrado", 404

    dados = {
        "status": status,
        "foto_servico": request.form.get("foto_servico") == "on",
        "assinatura_cliente": request.form.get("assinatura_cliente") == "on",
        "epi_utilizado": request.form.get("epi_utilizado") == "on",
    }
    if status == "Rascunho":
        dados["tipo"] = "Rascunho"
    elif servico["tipo"] == "Rascunho":
        status = "Rascunho"
        dados["status"] = status

    finalizados = ["Concluído", "Finalizado Bling"]
    data_conclusao = datetime.now().isoformat(timespec="seconds") if status in finalizados else None
    dados["data_conclusao"] = data_conclusao
    
    supabase.table("3_ata_servicos").update(dados).eq("id", servico_id).execute()
    if status in finalizados:
        supabase.table("3_ata_historico").insert({
            "servico_id": servico_id,
            "texto": f"Serviço marcado como {status.lower()}.",
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
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port, debug=False)

