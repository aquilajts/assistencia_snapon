from flask import Flask, render_template, request, redirect, url_for, jsonify
import sqlite3
from datetime import datetime, date
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "servicos.db"

app = Flask(__name__)


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS servicos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tipo TEXT NOT NULL,
            regiao TEXT NOT NULL,
            cliente TEXT NOT NULL,
            endereco TEXT DEFAULT '',
            data_prevista TEXT,
            observacoes TEXT DEFAULT '',
            status TEXT NOT NULL DEFAULT 'A confirmar',
            data_conclusao TEXT,
            criado_em TEXT NOT NULL
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS historico (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            servico_id INTEGER NOT NULL,
            texto TEXT NOT NULL,
            criado_em TEXT NOT NULL,
            FOREIGN KEY(servico_id) REFERENCES servicos(id)
        )
    """)
    conn.commit()
    conn.close()


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
        endereco = request.form.get("endereco", "").strip()
        data_prevista = request.form.get("data_prevista", "")
        observacoes = request.form.get("observacoes", "").strip()
        status = "Agendado" if data_prevista and cliente and endereco else "A confirmar"

        if not cliente:
            return render_template("novo_servico.html", erro="Informe o cliente/empresa.")

        conn = get_db()
        cur = conn.execute("""
            INSERT INTO servicos
            (tipo, regiao, cliente, endereco, data_prevista, observacoes, status, criado_em)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            tipo, regiao, cliente, endereco, data_prevista, observacoes,
            status, datetime.now().isoformat(timespec="seconds")
        ))
        servico_id = cur.lastrowid

        if observacoes:
            conn.execute(
                "INSERT INTO historico (servico_id, texto, criado_em) VALUES (?, ?, ?)",
                (servico_id, "Observação inicial: " + observacoes,
                 datetime.now().isoformat(timespec="seconds"))
            )
        conn.commit()
        conn.close()
        return redirect(url_for("detalhes", servico_id=servico_id))

    return render_template("novo_servico.html", erro=None)


@app.route("/servicos/<int:servico_id>")
def detalhes(servico_id):
    conn = get_db()
    servico = conn.execute(
        "SELECT * FROM servicos WHERE id = ?", (servico_id,)
    ).fetchone()
    historico = conn.execute(
        "SELECT * FROM historico WHERE servico_id = ? ORDER BY criado_em DESC",
        (servico_id,)
    ).fetchall()
    conn.close()

    if not servico:
        return "Serviço não encontrado", 404

    return render_template("detalhes.html", servico=servico, historico=historico)


@app.route("/servicos/<int:servico_id>/status", methods=["POST"])
def alterar_status(servico_id):
    status = request.form.get("status", "")
    permitidos = ["A confirmar", "Agendado", "Em andamento", "Concluído", "Problema / Retorno necessário"]
    if status not in permitidos:
        return redirect(url_for("detalhes", servico_id=servico_id))

    conn = get_db()
    data_conclusao = datetime.now().isoformat(timespec="seconds") if status == "Concluído" else None
    conn.execute(
        "UPDATE servicos SET status = ?, data_conclusao = ? WHERE id = ?",
        (status, data_conclusao, servico_id)
    )
    if status == "Concluído":
        conn.execute(
            "INSERT INTO historico (servico_id, texto, criado_em) VALUES (?, ?, ?)",
            (servico_id, "Serviço marcado como concluído.",
             datetime.now().isoformat(timespec="seconds"))
        )
    conn.commit()
    conn.close()
    return redirect(url_for("detalhes", servico_id=servico_id))


@app.route("/servicos/<int:servico_id>/observacao", methods=["POST"])
def adicionar_observacao(servico_id):
    texto = request.form.get("texto", "").strip()
    if texto:
        conn = get_db()
        conn.execute(
            "INSERT INTO historico (servico_id, texto, criado_em) VALUES (?, ?, ?)",
            (servico_id, texto, datetime.now().isoformat(timespec="seconds"))
        )
        conn.commit()
        conn.close()
    return redirect(url_for("detalhes", servico_id=servico_id))


@app.route("/api/servicos")
def api_servicos():
    conn = get_db()
    rows = conn.execute("SELECT * FROM servicos ORDER BY data_prevista ASC, id DESC").fetchall()
    conn.close()
    return jsonify([dict(row) for row in rows])


init_db()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
