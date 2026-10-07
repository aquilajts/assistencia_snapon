from flask import Flask, render_template, request, redirect, url_for, jsonify
import os
from datetime import datetime, date
from supabase import create_client, Client

app = Flask(__name__)

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")

#SUPABASE_URL = "https://maxdqycohsopgeacpyoy.supabase.co"
#SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im1heGRxeWNvaHNvcGdlYWNweW95Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTE5ODY5MzEsImV4cCI6MjA2NzU2MjkzMX0.Noj3VmkV3zJ3iRlptetkIzL9g_-ZU4wx_gnhzLMFyMA"

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)


@app.context_processor
def utility_processor():
    return {"today": date.today().isoformat()}


@app.route("/")
def index():
    hoje = date.today().isoformat()
    inicio_semana = date.today().toordinal() - date.today().weekday()
    semana = date.fromordinal(inicio_semana)
    fim_semana = date.fromordinal(inicio_semana + 6)

    total_hoje = supabase.table("3_ata_servicos") \
        .select("id", count="exact") \
        .eq("data_prevista", hoje) \
        .execute().count or 0

    pendentes = supabase.table("3_ata_servicos") \
        .select("id", count="exact") \
        .neq("status", "Concluído") \
        .execute().count or 0

    semana_total = supabase.table("3_ata_servicos") \
        .select("id", count="exact") \
        .gte("data_prevista", semana.isoformat()) \
        .lte("data_prevista", fim_semana.isoformat()) \
        .execute().count or 0

    regioes = {}

    for regiao in ["Norte", "Sul", "Grande Vitória"]:
        regioes[regiao] = supabase.table("3_ata_servicos") \
            .select("id", count="exact") \
            .eq("regiao", regiao) \
            .neq("status", "Concluído") \
            .execute().count or 0

    return render_template(
        "index.html",
        total_hoje=total_hoje,
        pendentes=pendentes,
        semana_total=semana_total,
        regioes=regioes
    )

@app.route("/servicos")
def servicos():
    response = supabase.table("3_ata_servicos") \
        .select("*") \
        .order("data_prevista", desc=False, nullsfirst=False) \
        .order("id", desc=True) \
        .execute()

    rows = response.data

    return render_template("servicos.html", servicos=rows)


@app.route("/servicos/novo", methods=["GET", "POST"])
def novo_servico():
    if request.method == "POST":
        tipo = request.form.get("tipo", "Assistência Técnica")
        regiao = request.form.get("regiao", "Grande Vitória")
        cliente = request.form.get("cliente", "").strip()
        telefone = request.form.get("telefone", "").strip()
        endereco = request.form.get("endereco", "").strip()
        data_prevista = request.form.get("data_prevista", "")
        observacoes = request.form.get("observacoes", "").strip()
        status = "A confirmar"

        if not cliente:
            return render_template("novo_servico.html", erro="Informe o cliente/empresa.")

        cur = supabase.table("3_ata_servicos").insert({
            "tipo": tipo,
            "regiao": regiao,
            "cliente": cliente,
            "telefone": telefone,
            "endereco": endereco,
            "data_prevista": data_prevista or None,
            "observacoes": observacoes,
            "status": "A confirmar",
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

    return render_template("novo_servico.html", erro=None)


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

    if request.method == "POST":
        dados = {
            "tipo": request.form.get("tipo", ""),
            "regiao": request.form.get("regiao", ""),
            "cliente": request.form.get("cliente", "").strip(),
            "telefone": request.form.get("telefone", "").strip(),
            "endereco": request.form.get("endereco", "").strip(),
            "data_prevista": request.form.get("data_prevista", ""),
            "observacoes": request.form.get("observacoes", "").strip(),
        }
        data_prevista_input = dados["data_prevista"]

        if not dados["cliente"]:
            erro = "Informe o cliente/empresa."
            servico.update(dados)
        else:
            dados["data_prevista"] = dados["data_prevista"] or None
            supabase.table("3_ata_servicos").update(dados).eq("id", servico_id).execute()
            return redirect(url_for("detalhes", servico_id=servico_id))

    return render_template(
        "editar_servico.html",
        servico=servico,
        data_prevista_input=data_prevista_input,
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
    
    historico_response = supabase.table("3_ata_historico") \
        .select("*") \
        .eq("servico_id", servico_id) \
        .order("criado_em", desc=True) \
        .execute()
    
    historico = historico_response.data

    if not servico:
        return "Serviço não encontrado", 404

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
    permitidos = ["A confirmar", "Agendado", "Em andamento", "Concluído", "Problema / Retorno necessário"]
    if status not in permitidos:
        return redirect(url_for("detalhes", servico_id=servico_id))

    data_conclusao = datetime.now().isoformat(timespec="seconds") if status == "Concluído" else None
    
    supabase.table("3_ata_servicos").update({
        "status": status,
        "data_conclusao": data_conclusao
    }).eq("id", servico_id).execute()
    if status == "Concluído":
        supabase.table("3_ata_historico").insert({
            "servico_id": servico_id,
            "texto": "Serviço marcado como concluído.",
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

    return jsonify(response.data)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
