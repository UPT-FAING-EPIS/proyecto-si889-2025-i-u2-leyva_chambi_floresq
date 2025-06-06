document.addEventListener("DOMContentLoaded", () => {
    checkAuth(); // Asegúrate de que el usuario esté autenticado
    
    const searchBtn = document.getElementById("searchBtn");
    const loadMoreBtn = document.getElementById("loadMoreBtn");
    
    let currentPage = 1;
    let currentSearch = "";
    
    searchBtn.addEventListener("click", () => {
        currentPage = 1;
        currentSearch = document.getElementById("documentSearch").value.trim();
        searchVersions(currentSearch, currentPage);
    });
    
    loadMoreBtn.addEventListener("click", (e) => {
        e.preventDefault();
        currentPage++;
        searchVersions(currentSearch, currentPage);
    });
    
    // Agregar evento para cerrar el modal al hacer clic en el botón cerrar
    document.addEventListener('click', (e) => {
        if (e.target.classList.contains('close-preview') || 
            e.target.id === 'previewModal' && e.target === e.currentTarget) {
            document.getElementById('previewModal').style.display = 'none';
        }
    });
});

async function searchVersions(documentTitle, page) {
    const versionsList = document.getElementById("versionsList");
    const loadMoreContainer = document.getElementById("loadMoreContainer");
    
    if (page === 1) {
        versionsList.innerHTML = ""; // Limpiar solo en la primera página
    }
    
    if (!documentTitle) {
        versionsList.innerHTML = "<li class='list-group-item'>Por favor, introduce un nombre de documento.</li>";
        loadMoreContainer.style.display = "none";
        return;
    }
    
    try {
        const response = await fetch(`/api/documents/versions/?title=${encodeURIComponent(documentTitle)}&page=${page}&limit=10`, {
            method: "GET",
            headers: { 
                "Authorization": `Bearer ${localStorage.getItem("access_token")}` 
            }
        });
        
        const data = await response.json();
        
        if (!response.ok) {
            throw new Error(data.detail || "Error al buscar versiones");
        }
        
        if (data.versions.length === 0 && page === 1) {
            versionsList.innerHTML = "<li class='list-group-item'>No se encontraron versiones para este documento.</li>";
            loadMoreContainer.style.display = "none";
            return;
        }
        
        data.versions.forEach(version => {
            const li = createVersionItem(version);
            versionsList.appendChild(li);
        });
        
        loadMoreContainer.style.display = data.has_more ? "block" : "none";
        
    } catch (error) {
        console.error("Error:", error);
        alert("Ocurrió un error: " + error.message);
    }
}

function createVersionItem(version) {
    const li = document.createElement("li");
    li.className = "list-group-item d-flex justify-content-between align-items-center";
    
    // Contenedor para título, versión y fecha (izquierda)
    const leftContent = document.createElement("div");

    // Enlace de descarga para el título
    const downloadLink = createLink(`/api/documents/download/${version.document_id}`, version.title, "text-decoration-none text-primary");
    
    // Texto normal negro para la versión
    const versionSpan = createTextSpan(`Versión ${version.version_number}`, "#000");
    
    // Fecha en gris
    const dateSpan = createTextSpan(new Date(version.created_at).toLocaleString(), "text-muted", "small");
    
    leftContent.appendChild(downloadLink);
    leftContent.appendChild(versionSpan);
    leftContent.appendChild(dateSpan);
    
    // Contenedor para botones (derecha)
    const actionsContainer = document.createElement("div");
    
    // Botón de previsualizar
    const previewBtn = createActionBtn("Previsualizar", () => previewDocument(version.document_id), "text-primary me-3");
    
    // Botón de eliminar
    const deleteBtn = createActionBtn("Eliminar", () => deleteVersion(version.document_id, version.version_number), "text-danger");
    
    actionsContainer.appendChild(previewBtn);
    actionsContainer.appendChild(deleteBtn);
    
    li.appendChild(leftContent);
    li.appendChild(actionsContainer);
    
    return li;
}

function createLink(href, text, classNames = "") {
    const link = document.createElement("a");
    link.href = href;
    link.target = "_blank";
    link.className = classNames;
    link.textContent = text;
    return link;
}

function createTextSpan(text, color, extraClass = "") {
    const span = document.createElement(extraClass ? "small" : "span");
    span.className = extraClass;
    span.style.color = color;
    span.textContent = text;
    return span;
}

function createActionBtn(text, onClick, classNames) {
    const btn = document.createElement("a");
    btn.href = "#";
    btn.className = classNames;
    btn.textContent = text;
    btn.onclick = (e) => {
        e.preventDefault();
        onClick();
    };
    return btn;
}

async function deleteVersion(documentId, versionNumber) {
    if (!confirm("¿Estás seguro de que deseas eliminar esta versión?")) {
        return;
    }
    
    try {
        const response = await fetch(`/api/documents/versions/${documentId}/${versionNumber}`, {
            method: "DELETE",
            headers: { 
                "Authorization": `Bearer ${localStorage.getItem("access_token")}` 
            }
        });
        
        if (response.ok) {
            // Recargar la lista o eliminar el elemento visualmente
            currentPage = 1;
            searchVersions(currentSearch, currentPage);
            
            showAlert("Versión eliminada correctamente", "success");
        } else {
            const data = await response.json();
            throw new Error(data.detail || "Error al eliminar la versión");
        }
    } catch (error) {
        console.error("Error:", error);
        showAlert("Ocurrió un error: " + error.message, "danger");
    }
}

async function previewDocument(documentId) {
    try {
        const response = await fetch(`/api/documents/content/${documentId}`, {
            method: "GET",
            headers: { 
                "Authorization": `Bearer ${localStorage.getItem("access_token")}` 
            }
        });
        
        if (!response.ok) {
            const data = await response.json();
            throw new Error(data.detail || "Error al obtener el contenido del documento");
        }
        
        const data = await response.json();
        
        const modal = document.getElementById('previewModal');
        const titleElement = document.getElementById('previewTitle');
        const contentElement = document.getElementById('previewContent');
        
        titleElement.textContent = `${data.title} (Versión ${data.version})`;
        contentElement.innerHTML = marked.parse(data.markdown_content);
        
        modal.style.display = 'block';
        
    } catch (error) {
        console.error("Error:", error);
        showAlert("Ocurrió un error: " + error.message, "danger");
    }
}
