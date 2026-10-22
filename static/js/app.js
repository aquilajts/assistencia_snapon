document.addEventListener("DOMContentLoaded", () => {
    const driverWarning = document.querySelector("#driver-warning-dialog");
    if (driverWarning) {
        driverWarning.showModal();
        driverWarning.querySelector("[data-close-driver-warning]")
            .addEventListener("click", () => driverWarning.close());
        driverWarning.addEventListener("click", event => {
            if (event.target === driverWarning) driverWarning.close();
        });
    }

    document.querySelectorAll("[data-service-equipment-form], [data-registration-form]").forEach(form => {
        const status = form.querySelector('[name="status"]');
        if (!status) return;
        const error = document.querySelector("#equipment-confirmation-error");
        form.addEventListener("submit", event => {
            if (status.value !== "Agendado") return;
            let todosConfirmados;
            if (form.matches("[data-registration-form]")) {
                const equipamentos = JSON.parse(
                    form.querySelector("#equipamentos-json").value || "[]"
                );
                todosConfirmados = equipamentos.every(equipamento =>
                    equipamento.levado === true
                    && equipamento.ferramentas.every(ferramenta => ferramenta.levado === true)
                );
            } else {
                todosConfirmados = [...document.querySelectorAll("[data-equipment-confirmation-item]")]
                    .every(item => item.checked);
            }
            if (todosConfirmados) {
                if (error) error.classList.add("hidden");
                return;
            }
            event.preventDefault();
            if (error) {
                error.textContent = "Marque todos os equipamentos e ferramentas antes de agendar.";
                error.classList.remove("hidden");
                error.scrollIntoView({ behavior: "smooth", block: "center" });
            }
        });
    });

    const registrationForm = document.querySelector("[data-registration-form]");
    if (registrationForm) {
        const typeOptions = [...registrationForm.querySelectorAll('[name="tipo"]')];
        const statusSelect = registrationForm.querySelector('[name="status"]');

        function updateRegistrationStatuses() {
            const isDraft = registrationForm.querySelector('[name="tipo"]:checked')?.value === "Rascunho";
            [...statusSelect.options].forEach(option => {
                const isDraftOption = option.value === "Rascunho";
                option.hidden = isDraftOption !== isDraft;
                option.disabled = isDraftOption !== isDraft;
            });
            statusSelect.value = isDraft
                ? "Rascunho"
                : statusSelect.value === "Rascunho" ? "A confirmar" : statusSelect.value;
        }

        typeOptions.forEach(option => option.addEventListener("change", updateRegistrationStatuses));
        updateRegistrationStatuses();
    }

    const catalogCategoryFilter = document.querySelector("#catalog-category-filter");
    if (catalogCategoryFilter) {
        const equipmentLinks = [
            ...document.querySelectorAll(".catalog-equipment-link"),
        ];
        catalogCategoryFilter.addEventListener("change", () => {
            equipmentLinks.forEach(link => {
                link.classList.toggle(
                    "hidden",
                    Boolean(catalogCategoryFilter.value)
                        && link.dataset.category !== catalogCategoryFilter.value
                );
            });
        });
        catalogCategoryFilter.dispatchEvent(new Event("change"));
    }

    const catalogEditor = document.querySelector("#equipment-catalog-editor");
    if (catalogEditor) {
        const toolList = document.querySelector("#catalog-tools-list");
        const addToolButton = document.querySelector("#add-catalog-tool");
        const toolCount = document.querySelector("#tool-count");

        function updateToolCount() {
            const rows = [...toolList.querySelectorAll(".catalog-tool-row")];
            toolCount.textContent = String(rows.length);
            addToolButton.disabled = rows.length >= 30;
        }

        addToolButton.addEventListener("click", () => {
            if (toolList.querySelectorAll(".catalog-tool-row").length >= 30) return;
            const row = document.createElement("div");
            row.className = "catalog-tool-row";
            const input = document.createElement("input");
            input.type = "text";
            input.name = "ferramentas";
            input.maxLength = 120;
            input.placeholder = "Nome da ferramenta";
            const removeButton = document.createElement("button");
            removeButton.type = "button";
            removeButton.className = "button ghost remove-tool";
            removeButton.textContent = "Excluir ferramenta";
            row.append(input, removeButton);
            toolList.append(row);
            updateToolCount();
            input.focus();
        });

        toolList.addEventListener("click", event => {
            if (!(event.target instanceof Element)) return;
            const button = event.target.closest(".remove-tool");
            if (!button) return;
            button.closest(".catalog-tool-row").remove();
            updateToolCount();
        });
        updateToolCount();
    }

    document.querySelectorAll(".catalog-delete-form").forEach(form => {
        form.addEventListener("submit", event => {
            const name = form.dataset.confirmDelete;
            if (!window.confirm(`Excluir o equipamento "${name}"?`)) {
                event.preventDefault();
            }
        });
    });

    const equipmentSection = document.querySelector("#equipment-section");
    if (equipmentSection) {
        const catalog = JSON.parse(
            document.querySelector("#catalogo-equipamentos").textContent
        );
        const categorySelect = document.querySelector("#equipment-category");
        const equipmentSelect = document.querySelector("#equipment-choice");
        const serviceToolsField = document.querySelector("#service-tools-field");
        const serviceToolsInput = document.querySelector("#service-tools");
        const assemblyToolsPreview = document.querySelector("#assembly-tools-preview");
        const assemblyToolsList = document.querySelector("#assembly-tools-list");
        const equipmentDialog = document.querySelector("#equipment-dialog");
        const equipmentDialogError = document.querySelector("#equipment-dialog-error");
        const equipmentList = document.querySelector("#equipment-list");
        const equipmentInput = document.querySelector("#equipamentos-json");
        const addEquipmentButton = document.querySelector("#add-equipment");
        const checkAllEquipment = document.querySelector("#check-all-equipment");
        let equipmentItems = JSON.parse(equipmentInput.value || "[]");

        [...new Set(catalog.map(item => item.categoria))].forEach(category => {
            const option = document.createElement("option");
            option.value = category;
            option.textContent = category;
            categorySelect.append(option);
        });

        function closeEquipmentDialog() {
            equipmentDialog.close();
            equipmentDialogError.classList.add("hidden");
        }

        function renderEquipmentItems() {
            equipmentList.replaceChildren();
            equipmentItems.forEach((item, equipmentIndex) => {
                item.levado = item.levado === true;
                item.ferramentas.forEach(tool => {
                    tool.levado = tool.levado === true;
                });
                const card = document.createElement("article");
                card.className = "equipment-card";

                const heading = document.createElement("div");
                heading.className = "equipment-card-head";
                const title = document.createElement("div");
                const equipmentLabel = document.createElement("label");
                equipmentLabel.className = "equipment-confirmation-item";
                const equipmentCheckbox = document.createElement("input");
                equipmentCheckbox.type = "checkbox";
                equipmentCheckbox.checked = item.levado;
                equipmentCheckbox.dataset.equipmentConfirmationItem = "";
                equipmentCheckbox.addEventListener("change", () => {
                    equipmentItems[equipmentIndex].levado = equipmentCheckbox.checked;
                    updateEquipmentInput();
                });
                const name = document.createElement("span");
                name.className = "equipment-name";
                name.textContent = item.equipamento;
                equipmentLabel.append(equipmentCheckbox, name);
                const category = document.createElement("p");
                category.className = "muted small";
                category.textContent = `${item.categoria} · ${item.tipo}`;
                title.append(equipmentLabel, category);

                const removeButton = document.createElement("button");
                removeButton.type = "button";
                removeButton.className = "button ghost";
                removeButton.textContent = "Remover";
                removeButton.addEventListener("click", () => {
                    equipmentItems.splice(equipmentIndex, 1);
                    renderEquipmentItems();
                });
                heading.append(title, removeButton);
                card.append(heading);

                if (item.ferramentas.length) {
                    const tools = document.createElement("div");
                    tools.className = "equipment-tools";
                    item.ferramentas.forEach((tool, toolIndex) => {
                        const label = document.createElement("label");
                        const checkbox = document.createElement("input");
                        checkbox.type = "checkbox";
                        checkbox.checked = tool.levado;
                        checkbox.dataset.equipmentConfirmationItem = "";
                        checkbox.addEventListener("change", () => {
                            equipmentItems[equipmentIndex].ferramentas[toolIndex].levado =
                                checkbox.checked;
                            updateEquipmentInput();
                        });
                        const toolName = document.createElement("span");
                        toolName.textContent = tool.nome;
                        label.append(checkbox, toolName);
                        tools.append(label);
                    });
                    card.append(tools);
                } else {
                    const noTools = document.createElement("p");
                    noTools.className = "muted small";
                    noTools.textContent = "Nenhuma ferramenta registrada para este equipamento.";
                    card.append(noTools);
                }
                equipmentList.append(card);
            });
            updateEquipmentInput();
            addEquipmentButton.disabled = equipmentItems.length >= 6 || catalog.length === 0;
        }

        function updateEquipmentInput() {
            equipmentInput.value = JSON.stringify(equipmentItems);
            const allItems = equipmentItems.flatMap(item => [
                item,
                ...item.ferramentas,
            ]);
            checkAllEquipment.checked = allItems.length > 0
                && allItems.every(item => item.levado);
            checkAllEquipment.indeterminate = allItems.some(item => item.levado)
                && !checkAllEquipment.checked;
        }

        checkAllEquipment.addEventListener("change", () => {
            equipmentItems.forEach(item => {
                item.levado = checkAllEquipment.checked;
                item.ferramentas.forEach(tool => {
                    tool.levado = checkAllEquipment.checked;
                });
            });
            renderEquipmentItems();
        });

        function updateEquipmentChoices() {
            const category = categorySelect.value;
            const options = catalog.filter(item => item.categoria === category);
            equipmentSelect.replaceChildren();
            const placeholder = document.createElement("option");
            placeholder.value = "";
            placeholder.textContent = category
                ? "Selecione um equipamento"
                : "Selecione primeiro a categoria";
            equipmentSelect.append(placeholder);
            options.forEach(item => {
                const option = document.createElement("option");
                option.value = String(item.id);
                option.textContent = item.equipamento;
                equipmentSelect.append(option);
            });
            equipmentSelect.disabled = options.length === 0;
            updateServiceToolsVisibility();
        }

        function updateServiceToolsVisibility() {
            const selected = catalog.find(
                item => String(item.id) === equipmentSelect.value
            );
            const isService = selected?.tipo === "Serviço";
            const isAssembly = selected?.tipo === "Montagem";
            serviceToolsField.classList.toggle("hidden", !isService);
            assemblyToolsPreview.classList.toggle("hidden", !isAssembly);
            assemblyToolsList.replaceChildren();
            if (isAssembly) {
                (selected.ferramentas || []).forEach(tool => {
                    const item = document.createElement("li");
                    item.textContent = tool;
                    assemblyToolsList.append(item);
                });
            }
            if (!isService) serviceToolsInput.value = "";
        }

        addEquipmentButton.addEventListener("click", () => {
            if (equipmentItems.length >= 6) return;
            categorySelect.value = "";
            equipmentSelect.replaceChildren();
            const placeholder = document.createElement("option");
            placeholder.value = "";
            placeholder.textContent = "Selecione primeiro a categoria";
            equipmentSelect.append(placeholder);
            equipmentSelect.disabled = true;
            serviceToolsInput.value = "";
            serviceToolsField.classList.add("hidden");
            assemblyToolsPreview.classList.add("hidden");
            assemblyToolsList.replaceChildren();
            equipmentDialog.showModal();
        });
        categorySelect.addEventListener("change", updateEquipmentChoices);
        equipmentSelect.addEventListener("change", updateServiceToolsVisibility);
        document.querySelector("#close-equipment-dialog")
            .addEventListener("click", closeEquipmentDialog);
        document.querySelector("#cancel-equipment")
            .addEventListener("click", closeEquipmentDialog);
        document.querySelector("#save-equipment").addEventListener("click", () => {
            const selected = catalog.find(
                item => String(item.id) === equipmentSelect.value
            );
            if (!selected) {
                equipmentDialogError.textContent = "Selecione um equipamento.";
                equipmentDialogError.classList.remove("hidden");
                return;
            }

            const toolNames = selected.tipo === "Montagem"
                ? (selected.ferramentas || [])
                : serviceToolsInput.value.split(/\r?\n/).map(tool => tool.trim()).filter(Boolean);
            equipmentItems.push({
                catalogo_id: selected.id,
                categoria: selected.categoria,
                equipamento: selected.equipamento,
                tipo: selected.tipo,
                levado: false,
                ferramentas: [...new Set(toolNames)].map(nome => ({
                    nome,
                    levado: false,
                })),
            });
            renderEquipmentItems();
            closeEquipmentDialog();
        });

        equipmentDialog.addEventListener("click", event => {
            if (event.target === equipmentDialog) closeEquipmentDialog();
        });
        renderEquipmentItems();
    }

    const serviceEquipmentForm = document.querySelector("[data-service-equipment-form]");
    if (serviceEquipmentForm) {
        const checkboxes = [
            ...document.querySelectorAll("[data-equipment-confirmation-item]"),
        ];
        const checkAll = document.querySelector("#check-all-service-equipment");

        function updateCheckAllState() {
            checkAll.checked = checkboxes.length > 0
                && checkboxes.every(checkbox => checkbox.checked);
            checkAll.indeterminate = checkboxes.some(checkbox => checkbox.checked)
                && !checkAll.checked;
        }

        checkAll.addEventListener("change", () => {
            checkboxes.forEach(checkbox => {
                checkbox.checked = checkAll.checked;
            });
            checkAll.indeterminate = false;
        });
        checkboxes.forEach(checkbox => {
            checkbox.addEventListener("change", updateCheckAllState);
        });
        updateCheckAllState();
    }

    const collaboratorList = document.querySelector("#collaborator-list");
    const addCollaboratorButton = document.querySelector("#add-collaborator");
    if (collaboratorList && addCollaboratorButton) {
        function updateCollaboratorLimit() {
            const rows = [...collaboratorList.querySelectorAll(".collaborator-row")];
            addCollaboratorButton.disabled = rows.length >= 4;
        }

        collaboratorList.addEventListener("click", event => {
            if (!(event.target instanceof Element)) return;
            const removeButton = event.target.closest(".remove-collaborator");
            if (!removeButton) return;
            removeButton.closest(".collaborator-row").remove();
            updateCollaboratorLimit();
        });

        addCollaboratorButton.addEventListener("click", () => {
            if (collaboratorList.querySelectorAll(".collaborator-row").length >= 4) {
                return;
            }
            const row = document.createElement("div");
            row.className = "collaborator-row";
            const input = document.createElement("input");
            input.type = "text";
            input.name = "colaboradores";
            input.maxLength = 120;
            input.placeholder = "Nome do colaborador";
            const removeButton = document.createElement("button");
            removeButton.type = "button";
            removeButton.className = "button ghost remove-collaborator";
            removeButton.textContent = "Remover";
            row.append(input, removeButton);
            collaboratorList.append(row);
            updateCollaboratorLimit();
            input.focus();
        });

        updateCollaboratorLimit();
    }

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
