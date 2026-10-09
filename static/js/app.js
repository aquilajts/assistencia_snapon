document.addEventListener("DOMContentLoaded", () => {
    const cidade = document.querySelector("#cidade");
    const regiaoCidade = document.querySelector("#regiao");
    const municipios = [...document.querySelectorAll("#municipios option")];

    function atualizarRegiaoCidade() {
        if (!cidade || !regiaoCidade) return;
        const municipio = municipios.find(option => option.value === cidade.value);
        regiaoCidade.value = municipio?.dataset.regiao || "";
    }

    cidade?.addEventListener("input", atualizarRegiaoCidade);
    cidade?.addEventListener("change", atualizarRegiaoCidade);
    atualizarRegiaoCidade();

    const busca = document.querySelector("#busca");
    const tipo = document.querySelector("#filtroTipo");
    const regiao = document.querySelector("#filtroRegiao");
    const status = document.querySelector("#filtroStatus");
    const data = document.querySelector("#filtroData");
    const cards = [...document.querySelectorAll(".service-card")];
    const noResults = document.querySelector("#noResults");

    const params = new URLSearchParams(window.location.search);
    const selectedDate = params.get("date");
    const selectedType = params.get("type");
    const selectedStatus = params.get("status");
    if (selectedDate && data && [...data.options].some(option => option.value === selectedDate)) {
        data.value = selectedDate;
    }
    if (selectedType && tipo && [...tipo.options].some(option => option.value === selectedType || option.text === selectedType)) {
        tipo.value = selectedType;
    }
    if (selectedStatus && status && [...status.options].some(option => option.value === selectedStatus || option.text === selectedStatus)) {
        status.value = selectedStatus;
    }

    function filtrar() {
        if (!cards.length) return;
        const q = (busca?.value || "").toLowerCase().trim();
        const t = tipo?.value || "";
        const r = regiao?.value || "";
        const s = status?.value || "";
        const filtroData = data?.value || "today";
        const hoje = new Date();
        hoje.setHours(0, 0, 0, 0);
        const fimProximosCincoDias = new Date(hoje);
        fimProximosCincoDias.setDate(fimProximosCincoDias.getDate() + 4);
        const fimProximosDezDias = new Date(hoje);
        fimProximosDezDias.setDate(fimProximosDezDias.getDate() + 9);
        const inicioMes = new Date(hoje.getFullYear(), hoje.getMonth(), 1);
        const fimMes = new Date(hoje.getFullYear(), hoje.getMonth() + 1, 0);
        let visiveis = 0;

        cards.forEach(card => {
            const [ano, mes, dia] = (card.dataset.date || "").split("-").map(Number);
            const dataServico = ano && mes && dia
                ? new Date(ano, mes - 1, dia)
                : null;
            const dataMatch = filtroData === "all"
                || (dataServico && (
                    (filtroData === "today" && dataServico.getTime() === hoje.getTime())
                    || (filtroData === "next5" && dataServico >= hoje && dataServico <= fimProximosCincoDias)
                    || (filtroData === "next10" && dataServico >= hoje && dataServico <= fimProximosDezDias)
                    || (filtroData === "month" && dataServico >= inicioMes && dataServico <= fimMes)
                ));
            const statusMatch = s
                ? card.dataset.status === s
                : card.dataset.status !== "Finalizado Bling";
            const ok = (!q || card.dataset.search.includes(q))
                && (!t || card.dataset.tipo === t)
                && (!r || card.dataset.regiao === r)
                && dataMatch
                && statusMatch;
            card.style.display = ok ? "flex" : "none";
            if (ok) visiveis++;
        });

        if (noResults) noResults.classList.toggle("hidden", visiveis !== 0);
    }

    busca?.addEventListener("input", filtrar);
    [tipo, regiao, status, data].forEach(el => el?.addEventListener("change", filtrar));
    filtrar();
});
