document.addEventListener("DOMContentLoaded", () => {
    checkAuth();
    fetchDocuments();

    const uploadForm = document.getElementById("uploadForm");
    uploadForm.addEventListener("submit", async (e) => {
        e.preventDefault();
        const title = document.getElementById("title").value;
        const fileInput = document.getElementById("fileInput").files[0];

        const formData = new FormData();
        formData.append("file", fileInput);
        formData.append("title", title);
        formData.append("user_id", 1); // Ajustar el user_id (puedes almacenarlo en localStorage también)

        const response = await fetch("/api/documents/upload/", {
            method: "POST",
            headers: { Authorization: `Bearer ${localStorage.getItem("access_token")}` },
            body: formData
        });

        if (response.ok) {
            alert("Documento subido correctamente.");
            fetchDocuments();
        } else {
            alert("Error al subir el documento.");
        }
    });
});

async function fetchDocuments() {
    const list = document.getElementById("documentList");
    list.innerHTML = ""; // Limpiar la lista antes de agregar nuevos documentos

    const userId = 1; // Obtener el user_id adecuado

    try {
        const response = await fetch(`/api/documents/list/?user_id=${userId}`, {
            method: "GET",
            headers: { 
                "Authorization": `Bearer ${localStorage.getItem("access_token")}` 
            }
        });

        if (response.ok) {
            const data = await response.json();
            const documents = data.documents;

            if (documents.length === 0) {
                const li = document.createElement("li");
                li.className = "list-group-item";
                li.textContent = "No tienes documentos.";
                list.appendChild(li);
            } else {
                documents.forEach(doc => {
                    const li = document.createElement("li");
                    li.className = "list-group-item d-flex justify-content-between align-items-center";

                    // Crear div para el título y la versión
                    const infoDiv = document.createElement("div");
                    
                    // Crear el enlace
                    const link = document.createElement("a");
                    link.href = `/api/documents/download/${doc.document_id}`;
                    link.target = "_blank";
                    link.textContent = doc.title;
                    link.style.textDecoration = "none";
                    link.style.color = "#0d6efd";
                    link.style.fontWeight = "normal";

                    // Crear el texto de versión
                    const versionSpan = document.createElement("span");
                    versionSpan.textContent = ` Version ${doc.version}`;
                    versionSpan.style.marginLeft = "8px";
                    versionSpan.style.color = "#666";

                    // Agregar título y versión al div info
                    infoDiv.appendChild(link);
                    infoDiv.appendChild(versionSpan);
                    
                    // Div para botones
                    const buttonsDiv = document.createElement("div");
                    
                    // Botón de previsualización
                    const previewBtn = document.createElement("button");
                    previewBtn.className = "btn btn-sm btn-outline-info mx-1";
                    previewBtn.textContent = "Previsualizar";
                    previewBtn.addEventListener("click", () => previewDocument(doc.document_id));
                    
                    // Nuevo botón para mejorar
                    const improveBtn = document.createElement("button");
                    improveBtn.className = "btn btn-sm btn-outline-success";
                    improveBtn.textContent = "Mejorar con IA";
                    improveBtn.onclick = () => {
                        improveDocument(doc.document_id);
                    };

                    // Nuevo botón para analizar similitudes
                    const analyzeBtn = document.createElement("button");
                    analyzeBtn.className = "btn btn-sm btn-outline-warning mx-1";
                    analyzeBtn.textContent = "Analizar Similitudes";
                    analyzeBtn.onclick = () => {
                        analyzeSimilarities(doc.document_id);
                    };

                    // Agregar después de analyzeBtn
                    const publishBtn = document.createElement("button");
                    publishBtn.className = "btn btn-sm btn-outline-primary mx-1";
                    publishBtn.textContent = "Publicar";
                    publishBtn.onclick = () => {
                        showPublishOptions(doc.document_id);
                    };
                    
                    // Añadir botones al div de botones
                    buttonsDiv.appendChild(previewBtn);
                    buttonsDiv.appendChild(improveBtn);
                    buttonsDiv.appendChild(analyzeBtn);
                    buttonsDiv.appendChild(publishBtn);

                    // Agregar ambos divs al li
                    li.appendChild(infoDiv);
                    li.appendChild(buttonsDiv);

                    list.appendChild(li);
                });
            }
        } else {
            alert("Error al obtener documentos.");
        }
    } catch (error) {
        console.error("Error:", error);
        alert("Ocurrió un error al obtener los documentos.");
    }
}

// Función para mejorar un documento
async function improveDocument(documentId) {
    try {
        // Mostrar mensaje de carga
        const loadingModal = document.createElement("div");
        loadingModal.style.position = "fixed";
        loadingModal.style.top = "0";
        loadingModal.style.left = "0";
        loadingModal.style.width = "100%";
        loadingModal.style.height = "100%";
        loadingModal.style.backgroundColor = "rgba(0, 0, 0, 0.5)";
        loadingModal.style.display = "flex";
        loadingModal.style.justifyContent = "center";
        loadingModal.style.alignItems = "center";
        loadingModal.style.zIndex = "1000";
        
        const loadingContent = document.createElement("div");
        loadingContent.style.backgroundColor = "white";
        loadingContent.style.padding = "20px";
        loadingContent.style.borderRadius = "5px";
        loadingContent.style.textAlign = "center";
        
        const spinner = document.createElement("div");
        spinner.className = "spinner-border text-primary";
        spinner.setAttribute("role", "status");
        
        const loadingText = document.createElement("div");
        loadingText.textContent = "Mejorando documento... Esto puede tardar unos momentos.";
        loadingText.style.marginTop = "10px";
        
        loadingContent.appendChild(spinner);
        loadingContent.appendChild(loadingText);
        loadingModal.appendChild(loadingContent);
        document.body.appendChild(loadingModal);
        
        // Llamar a la API para mejorar el documento
        const response = await fetch(`/api/documents/improve/${documentId}`, {
            method: "POST",
            headers: { 
                "Authorization": `Bearer ${localStorage.getItem("access_token")}`,
                "Content-Type": "application/json" 
            }
        });
        
        // Eliminar modal de carga
        document.body.removeChild(loadingModal);
        
        if (!response.ok) {
            const data = await response.json();
            throw new Error(data.detail || "Error al mejorar el documento");
        }
        
        const data = await response.json();
        
        // Redirigir a la página de documento mejorado
        window.location.href = `/improved_document/${data.document_id}`;
        
    } catch (error) {
        console.error("Error:", error);
        alert("Ocurrió un error: " + error.message);
    }
}

// Función para previsualizar documentos (similar a la de version_history.js)
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
        
        // Obtener el modal
        const modal = document.getElementById('previewModal');
        const titleElement = document.getElementById('previewTitle');
        const contentElement = document.getElementById('previewContent');
        const closeBtn = document.querySelector('.close-preview');
        
        // Actualizar contenido
        titleElement.textContent = `${data.title} (Versión ${data.version})`;
        
        // Convertir Markdown a HTML usando marked.js
        contentElement.innerHTML = marked.parse(data.markdown_content);
        
        // Mostrar el modal
        modal.style.display = 'block';

        // Configurar evento para cerrar modal
        closeBtn.onclick = function() {
            modal.style.display = 'none';
        };

        // Cerrar al hacer clic fuera del contenido
        modal.onclick = function(event) {
            if (event.target === modal) {
                modal.style.display = 'none';
            }
        };

    } catch (error) {
        console.error("Error:", error);
        showAlert("Ocurrió un error: " + error.message, "danger");
    }
}

// Función para analizar similitudes
async function analyzeSimilarities(documentId) {
    try {
        // Mostrar modal de información del documento
        const response = await fetch(`/api/similarity/document-info/${documentId}`, {
            method: "GET",
            headers: {
                "Authorization": `Bearer ${localStorage.getItem("access_token")}`
            }
        });

        if (!response.ok) {
            const data = await response.json();
            throw new Error(data.detail || "Error al obtener información del documento");
        }

        const documentInfo = await response.json();
        showSimilarityModal(documentInfo);

    } catch (error) {
        console.error("Error:", error);
        alert("Ocurrió un error: " + error.message);
    }
}

// Función para mostrar el modal de similitudes
function showSimilarityModal(documentInfo) {
    // Crear modal dinámicamente
    const modalHTML = `
        <div id="similarityModal" class="modal" style="display: block; position: fixed; z-index: 1000; left: 0; top: 0; width: 100%; height: 100%; overflow: auto; background-color: rgba(0,0,0,0.4);">
            <div class="modal-content" style="background-color: #fefefe; margin: 5% auto; padding: 0; border: 1px solid #888; width: 90%; max-width: 900px; border-radius: 8px;">
                <div class="modal-header" style="padding: 20px; border-bottom: 1px solid #ddd; display: flex; justify-content: between; align-items: center;">
                    <h4 style="margin: 0; color: #333;">📊 Análisis de Similitudes</h4>
                    <button id="closeSimilarityModal" style="background: none; border: none; font-size: 24px; cursor: pointer; color: #666;">&times;</button>
                </div>
                <div class="modal-body" style="padding: 20px;">
                    <div class="document-info" style="background: #f8f9fa; padding: 15px; border-radius: 6px; margin-bottom: 20px;">
                        <h5 style="color: #495057; margin-bottom: 15px;">📄 Información del Documento</h5>
                        <div class="row">
                            <div class="col-md-6">
                                <p><strong>Título:</strong> ${documentInfo.title}</p>
                                <p><strong>Autor:</strong> ${documentInfo.author}</p>
                                <p><strong>Formato Original:</strong> ${documentInfo.original_format}</p>
                                <p><strong>Versión:</strong> ${documentInfo.version || 'N/A'}</p>
                            </div>
                            <div class="col-md-6">
                                <p><strong>Creado:</strong> ${documentInfo.created_at}</p>
                                <p><strong>Actualizado:</strong> ${documentInfo.updated_at}</p>
                                <p><strong>Palabras:</strong> ${documentInfo.statistics.word_count.toLocaleString()}</p>
                                <p><strong>Caracteres:</strong> ${documentInfo.statistics.character_count.toLocaleString()}</p>
                            </div>
                        </div>
                    </div>
                    
                    <div class="analysis-section">
                        <div class="d-flex justify-content-between align-items-center mb-3">
                            <h5 style="color: #495057; margin: 0;">🔍 Análisis de Similitudes</h5>
                            <button id="startAnalysisBtn" class="btn btn-primary" onclick="startSimilarityAnalysis(${documentInfo.document_id})">
                                <span class="spinner-border spinner-border-sm" role="status" aria-hidden="true" style="display: none;"></span>
                                Analizar Similitudes
                            </button>
                        </div>
                        <div id="analysisResults" style="min-height: 200px;">
                            <div class="text-center text-muted" style="padding: 60px 0;">
                                <i class="fas fa-search" style="font-size: 48px; margin-bottom: 15px;"></i>
                                <p>Haz clic en "Analizar Similitudes" para comenzar el análisis</p>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    `;

    // Agregar modal al DOM
    document.body.insertAdjacentHTML('beforeend', modalHTML);

    // Configurar eventos
    document.getElementById('closeSimilarityModal').onclick = function() {
        document.getElementById('similarityModal').remove();
    };

    // Cerrar al hacer clic fuera del contenido
    document.getElementById('similarityModal').onclick = function(event) {
        if (event.target.id === 'similarityModal') {
            document.getElementById('similarityModal').remove();
        }
    };
}

// Función para iniciar el análisis de similitudes
async function startSimilarityAnalysis(documentId) {
    const btn = document.getElementById('startAnalysisBtn');
    const spinner = btn.querySelector('.spinner-border');
    const resultsDiv = document.getElementById('analysisResults');

    try {
        // Mostrar spinner y deshabilitar botón
        spinner.style.display = 'inline-block';
        btn.disabled = true;
        btn.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Analizando...';

        // Mostrar mensaje de carga
        resultsDiv.innerHTML = `
            <div class="text-center">
                <div class="spinner-border text-primary" role="status" style="width: 3rem; height: 3rem;">
                    <span class="visually-hidden">Cargando...</span>
                </div>
                <p class="mt-3">Analizando similitudes con otros documentos...</p>
                <p class="text-muted">Esto puede tardar unos momentos</p>
            </div>
        `;

        // Realizar análisis
        const response = await fetch(`/api/similarity/analyze-similarities/${documentId}`, {
            method: "POST",
            headers: {
                "Authorization": `Bearer ${localStorage.getItem("access_token")}`,
                "Content-Type": "application/json"
            }
        });

        // CAMBIO CRÍTICO: Verificar el tipo de contenido antes de parsear
        const contentType = response.headers.get('content-type');
        console.log('Response status:', response.status);
        console.log('Content-Type:', contentType);

        if (!response.ok) {
            let errorMessage;
            
            // Si es JSON, parsear como JSON
            if (contentType && contentType.includes('application/json')) {
                const errorData = await response.json();
                errorMessage = errorData.detail || "Error al analizar similitudes";
            } else {
                // Si no es JSON, leer como texto
                const errorText = await response.text();
                console.error('Error response (text):', errorText);
                errorMessage = `Error del servidor: ${response.status}`;
            }
            
            throw new Error(errorMessage);
        }

        // Verificar que la respuesta exitosa sea JSON
        if (!contentType || !contentType.includes('application/json')) {
            const text = await response.text();
            console.error('Expected JSON but got:', text);
            throw new Error('El servidor no devolvió una respuesta JSON válida');
        }

        const results = await response.json();
        displaySimilarityResults(results);

    } catch (error) {
        console.error("Error completo:", error);
        resultsDiv.innerHTML = `
            <div class="alert alert-danger">
                <h6>Error en el análisis</h6>
                <p>${error.message}</p>
                <small>Revisa la consola del navegador para más detalles</small>
            </div>
        `;
    } finally {
        // Restaurar botón
        btn.disabled = false;
        btn.innerHTML = 'Analizar Similitudes';
    }
}

// Función para mostrar los resultados del análisis
function displaySimilarityResults(results) {
    const resultsDiv = document.getElementById('analysisResults');

    if (results.comparisons.length === 0) {
        resultsDiv.innerHTML = `
            <div class="alert alert-info">
                <h6>Sin comparaciones disponibles</h6>
                <p>${results.message || 'No se encontraron otros documentos para comparar'}</p>
            </div>
        `;
        return;
    }

    let html = `
        <div class="results-summary mb-3">
            <div class="alert alert-info">
                <strong>📊 Resumen del Análisis:</strong> Se comparó con ${results.total_comparisons} documentos de otros usuarios.
            </div>
        </div>
        <div class="similarity-results">
    `;

    results.comparisons.forEach((comparison, index) => {
        html += `
            <div class="similarity-item mb-3 p-3" style="border: 1px solid #dee2e6; border-radius: 6px; background: #f8f9fa;">
                <div class="d-flex justify-content-between align-items-start">
                    <div class="flex-grow-1">
                        <h6 class="mb-1">${comparison.title}</h6>
                        <p class="text-muted mb-1">Autor: ${comparison.author}</p>
                        <small class="text-muted">ID: ${comparison.document_id}</small>
                    </div>
                    <div class="text-end">
                        <span class="badge bg-${comparison.classification.color} fs-6">
                            ${comparison.classification.icon} ${comparison.classification.percentage}%
                        </span>
                        <br>
                        <small class="text-muted">${comparison.classification.level}</small>
                    </div>
                </div>
            </div>
        `;
    });

    html += `</div>`;

    resultsDiv.innerHTML = html;
}

// Función para mostrar opciones de publicación
function showPublishOptions(documentId) {
    const optionsHTML = `
        <div id="publishModal" class="modal" style="display: block; position: fixed; z-index: 1000; left: 0; top: 0; width: 100%; height: 100%; background-color: rgba(0,0,0,0.4);">
            <div class="modal-content" style="background-color: #fefefe; margin: 15% auto; padding: 20px; border: 1px solid #888; width: 400px; border-radius: 8px;">
                <div class="modal-header" style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px;">
                    <h4 style="margin: 0;">📤 Opciones de Publicación</h4>
                    <button id="closePublishModal" style="background: none; border: none; font-size: 24px; cursor: pointer;">&times;</button>
                </div>
                <div class="modal-body">
                    <p>¿Cómo quieres publicar tu documento?</p>
                    <button class="btn btn-primary btn-block mb-2" onclick="publishAsReadme(${documentId})" style="width: 100%; margin-bottom: 10px;">
                        📝 Subir como README
                        <small class="d-block text-muted">Se creará/actualizará el README.md del repositorio</small>
                    </button>
                    <button class="btn btn-info btn-block" onclick="publishAsWiki(${documentId})" style="width: 100%;">
                        📚 Subir como Wiki
                        <small class="d-block text-muted">Se creará una página en la wiki del repositorio</small>
                    </button>
                </div>
            </div>
        </div>
    `;
    
    document.body.insertAdjacentHTML('beforeend', optionsHTML);
    
    document.getElementById('closePublishModal').onclick = function() {
        document.getElementById('publishModal').remove();
    };
}

// Función para publicar como README
function publishAsReadme(documentId) {
    document.getElementById('publishModal').remove();
    window.location.href = `/github/login?document_id=${documentId}&publish_type=readme`;
}

// Función para publicar como Wiki
function publishAsWiki(documentId) {
    document.getElementById('publishModal').remove();
    window.location.href = `/github/login?document_id=${documentId}&publish_type=wiki`;
}