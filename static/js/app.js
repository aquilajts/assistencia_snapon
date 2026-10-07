document.addEventListener("DOMContentLoaded", () => {
    const busca = document.querySelector("#busca");
    const tipo = document.querySelector("#filtroTipo");
    const regiao = document.querySelector("#filtroRegiao");
    const status = document.querySelector("#filtroStatus");
    const cards = [...document.querySelectorAll(".service-card")];
    const noResults = document.querySelector("#noResults");

    function filtrar() {
        if (!cards.length) return;
        const q = (busca?.value || "").toLowerCase().trim();
        const t = tipo?.value || "";
        const r = regiao?.value || "";
        const s = status?.value || "";
        let visiveis = 0;

        cards.forEach(card => {
            const ok = (!q || card.dataset.search.includes(q))
                && (!t || card.dataset.tipo === t)
                && (!r || card.dataset.regiao === r)
                && (!s || card.dataset.status === s);
            card.style.display = ok ? "flex" : "none";
            if (ok) visiveis++;
        });

        if (noResults) noResults.classList.toggle("hidden", visiveis !== 0);
    }

    [busca, tipo, regiao, status].forEach(el => el?.addEventListener("input", filtrar));
    [tipo, regiao, status].forEach(el => el?.addEventListener("change", filtrar));
});
