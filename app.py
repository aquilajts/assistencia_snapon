from flask import Flask, render_template, request, redirect, url_for, jsonify
import os
from datetime import datetime, date
from flask import Flask, render_template, request, redirect, url_for, jsonify
from supabase import create_client, Client

app = Flask(__name__)

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)


@app.context_processor
def utility_processor():
    return {"today": date.today().isoformat()}


@app.route("/")
def index():
    conn = get_db()
    hoje = date.today().isoformat()
    inicio_semana = (date.today().toordinal() - date.today().weekday())
    semana = date.fromordinal(inicio_semana)
    fim_semana = date.fromordinal(inicio_semana + 6)

    total_hoje = conn.execute(
        "SELECT COUNT(*) FROM servicos WHERE data_prevista = ?", (hoje,)
    ).fetchone()[0]
    pendentes = conn.execute(
        "SELECT COUNT(*) FROM servicos WHERE status != 'Concluído'"
    ).fetchone()[0]
    semana_total = conn.execute(
        "SELECT COUNT(*) FROM servicos WHERE data_prevista BETWEEN ? AND ?",
        (semana.isoformat(), fim_semana.isoformat())
    ).fetchone()[0]

    regioes = {}
    for regiao in ["Norte", "Sul", "Grande Vitória"]:
        regioes[regiao] = conn.execute(
            "SELECT COUNT(*) FROM servicos WHERE regiao = ? AND status != 'Concluído'",
            (regiao,)
        ).fetchone()[0]

    conn.close()
    return render_template(
        "index.html",
        total_hoje=total_hoje,
        pendentes=pendentes,
        semana_total=semana_total,
        regioes=regioes
    )


@app.route("/servicos")
def servicos():
    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM servicos ORDER BY CASE WHEN data_prevista IS NULL OR data_prevista='' THEN 1 ELSE 0 END, data_prevista ASC, id DESC"
    ).fetchall()
    conn.close()
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

        conn = get_db()
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
        servico_id = cur.lastrowid
        
        if observacoes:
            supabase.table("3_ata_historico").insert({
                "servico_id": servico_id,
                "texto": "Observação inicial: " + observacoes,
                "criado_em": datetime.now().isoformat(timespec="seconds")
            }).execute()
        return redirect(url_for("detalhes", servico_id=servico_id))

    return render_template("novo_servico.html", erro=None)


@app.route("/servicos/<int:servico_id>")
def detalhes(servico_id):
    servico_response = supabase.table("servicos") \
        .select("*") \
        .eq("id", servico_id) \
        .single() \
        .execute()
    
    servico = servico_response.data
    
    historico_response = supabase.table("historico") \
        .select("*") \
        .eq("servico_id", servico_id) \
        .order("criado_em", desc=True) \
        .execute()
    
    historico = historico_response.data

    if not servico:
        return "Serviço não encontrado", 404

    return render_template("detalhes.html", servico=servico, historico=historico)


@app.route("/servicos/<int:servico_id>/status", methods=["POST"])
def alterar_status(servico_id):
    status = request.form.get("status", "")
    permitidos = ["A confirmar", "Agendado", "Em andamento", "Concluído", "Problema / Retorno necessário"]
    if status not in permitidos:
        return redirect(url_for("detalhes", servico_id=servico_id))

    data_conclusao = datetime.now().isoformat(timespec="seconds") if status == "Concluído" else None
    
    supabase.table("servicos").update({
        "status": status,
        "data_conclusao": data_conclusao
    }).eq("id", servico_id).execute()
    if status == "Concluído":
        supabase.table("historico").insert({
            "servico_id": servico_id,
            "texto": "Serviço marcado como concluído.",
            "criado_em": datetime.now().isoformat(timespec="seconds")
        }).execute()
    return redirect(url_for("detalhes", servico_id=servico_id))


@app.route("/servicos/<int:servico_id>/observacao", methods=["POST"])
def adicionar_observacao(servico_id):
    texto = request.form.get("texto", "").strip()
        if texto:
            supabase.table("historico").insert({
                "servico_id": servico_id,
                "texto": texto,
                "criado_em": datetime.now().isoformat(timespec="seconds")
            }).execute()
    return redirect(url_for("detalhes", servico_id=servico_id))

@app.route("/servicos/<int:servico_id>/excluir", methods=["POST"])
def excluir_servico(servico_id):
    nome_confirmacao = request.form.get("nome_confirmacao", "").strip()

    servico_response = supabase.table("servicos") \
        .select("cliente") \
        .eq("id", servico_id) \
        .single() \
        .execute()

    servico = servico_response.data

    if not servico:
        return "Serviço não encontrado", 404

    if nome_confirmacao != servico["cliente"]:
        return redirect(url_for("detalhes", servico_id=servico_id))

    supabase.table("historico") \
        .delete() \
        .eq("servico_id", servico_id) \
        .execute()

    supabase.table("servicos") \
        .delete() \
        .eq("id", servico_id) \
        .execute()

    return redirect(url_for("servicos"))

@app.route("/api/servicos")
def api_servicos():
    response = supabase.table("servicos") \
        .select("*") \
        .order("data_prevista", desc=False) \
        .order("id", desc=True) \
        .execute()
    
    rows = response.data
    
    return render_template("servicos.html", servicos=rows)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
