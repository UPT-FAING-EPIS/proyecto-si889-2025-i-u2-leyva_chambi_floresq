document.addEventListener("DOMContentLoaded", () => {
    checkAuth();
    fetchDocuments();
    let selectedDocuments = [];
    let defaultDocumentId = null;
    let membersCount = 1;

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
                    <button class="btn btn-info btn-block" onclick="askForMultipleFiles(${documentId})" style="width: 100%;">
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


// Función para publicar como README (mantener funcionalidad original)
function publishAsReadme(documentId) {
    document.getElementById('publishModal').remove();
    window.location.href = `/github/login?document_id=${documentId}&publish_type=readme`;
}

// Función original para wiki único (mantener para compatibilidad)
function publishAsWiki(documentId) {
    document.getElementById('publishModal').remove();
    window.location.href = `/github/login?document_id=${documentId}&publish_type=wiki`;
}

function askForMultipleFiles(documentId) {
    document.getElementById('publishModal').remove();
    
    const multipleFilesHTML = `
        <div id="multipleFilesModal" class="modal" style="display: block; position: fixed; z-index: 1000; left: 0; top: 0; width: 100%; height: 100%; background-color: rgba(0,0,0,0.4);">
            <div class="modal-content" style="background-color: #fefefe; margin: 15% auto; padding: 20px; border: 1px solid #888; width: 450px; border-radius: 8px;">
                <div class="modal-header" style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px;">
                    <h4 style="margin: 0;">📚 Publicación en Wiki</h4>
                    <button id="closeMultipleFilesModal" style="background: none; border: none; font-size: 24px; cursor: pointer;">&times;</button>
                </div>
                <div class="modal-body" style="text-align: center;">
                    <p style="font-size: 18px; margin-bottom: 20px;">¿Deseas subir más archivos junto con este documento?</p>
                    <div style="display: flex; gap: 15px; justify-content: center;">
                        <button class="btn btn-secondary" onclick="publishSingleWiki(${documentId})" style="padding: 10px 20px;">
                            ❌ No, solo este
                        </button>
                        <button class="btn btn-primary" onclick="showDocumentSelector(${documentId})" style="padding: 10px 20px;">
                            ✅ Sí, seleccionar más
                        </button>
                    </div>
                </div>
            </div>
        </div>
    `;
    
    document.body.insertAdjacentHTML('beforeend', multipleFilesHTML);
    document.getElementById('closeMultipleFilesModal').onclick = function() {
        document.getElementById('multipleFilesModal').remove();
    };
}

// Función para publicar un solo documento como wiki (comportamiento original)
function publishSingleWiki(documentId) {
    document.getElementById('multipleFilesModal').remove();
    window.location.href = `/github/login?document_id=${documentId}&publish_type=wiki`;
}

// Función para mostrar el selector de documentos múltiples
async function showDocumentSelector(documentId) {
    document.getElementById('multipleFilesModal').remove();
    
    // Inicializar variables
    defaultDocumentId = documentId;
    selectedDocuments = [documentId]; // El documento original ya está seleccionado
    
    // Obtener todos los documentos del usuario
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
            
            showDocumentSelectorModal(documents, documentId);
        } else {
            alert("Error al obtener documentos.");
        }
    } catch (error) {
        console.error("Error:", error);
        alert("Ocurrió un error al obtener los documentos.");
    }
}

function showDocumentSelectorModal(documents, defaultDocId) {
    const selectorHTML = `
        <div id="documentSelectorModal" class="modal" style="display: block; position: fixed; z-index: 1000; left: 0; top: 0; width: 100%; height: 100%; background-color: rgba(0,0,0,0.4);">
            <div class="modal-content" style="background-color: #fefefe; margin: 2% auto; padding: 20px; border: 1px solid #888; width: 85%; max-width: 900px; border-radius: 8px; max-height: 90vh; overflow-y: auto;">
                <div class="modal-header" style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px;">
                    <h4 style="margin: 0;">📚 Seleccionar Documentos para Wiki</h4>
                    <button id="closeDocumentSelectorModal" style="background: none; border: none; font-size: 24px; cursor: pointer;">&times;</button>
                </div>
                <div class="modal-body">
                    <div style="margin-bottom: 15px; display: flex; justify-content: between; align-items: center;">
                        <p style="margin: 0; flex-grow: 1;">Selecciona los documentos que deseas publicar en tu wiki. El orden de selección será el orden de publicación.</p>
                        <button id="deselectAllBtn" class="btn btn-sm btn-outline-warning" style="margin-left: 10px;">
                            🔄 Deseleccionar Todo
                        </button>
                    </div>
                    <div id="selectedOrder" style="margin-bottom: 20px; padding: 10px; background-color: #f8f9fa; border-radius: 5px; min-height: 40px;">
                        <strong>Orden de publicación:</strong>
                        <div id="orderList" style="margin-top: 5px;"></div>
                    </div>
                    <div id="documentsList" style="max-height: 250px; overflow-y: auto; margin-bottom: 20px;">
                        ${generateDocumentsList(documents, defaultDocId)}
                    </div>
                    
                    <!-- Botones de publicación -->
                    <hr style="margin: 20px 0;">
                    <div style="text-align: center;">
                        <h5 style="margin-bottom: 20px; color: #333;">¿Cómo quieres publicar tu wiki?</h5>
                        
                        <div style="display: flex; gap: 20px; justify-content: center; flex-wrap: wrap;">
                            <!-- Botón para publicar solo documentos -->
                            <div style="text-align: center;">
                                <button id="publishOnlyDocsBtn" class="btn btn-primary btn-lg" style="padding: 15px 25px; margin-bottom: 10px; width: 280px;">
                                    📄 Solo Documentos
                                </button>
                                <p style="margin: 0; font-size: 12px; color: #666;">Publicar únicamente los documentos seleccionados</p>
                            </div>
                            
                            <!-- Botón para publicar con página Home -->
                            <div style="text-align: center;">
                                <button id="publishWithHomeBtn" class="btn btn-success btn-lg" style="padding: 15px 25px; margin-bottom: 10px; width: 280px;">
                                    🏠 Documentos + Página Home
                                </button>
                                <p style="margin: 0; font-size: 12px; color: #666;">Publicar documentos con una página de inicio personalizada</p>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    `;
    
    document.body.insertAdjacentHTML('beforeend', selectorHTML);
    
    // Event listeners
    document.getElementById('closeDocumentSelectorModal').onclick = function() {
        document.getElementById('documentSelectorModal').remove();
    };
    
    document.getElementById('deselectAllBtn').onclick = function() {
        deselectAll();
    };
    
    document.getElementById('publishOnlyDocsBtn').onclick = function() {
        publishOnlyDocuments();
    };
    
    document.getElementById('publishWithHomeBtn').onclick = function() {
        showHomePageForm();
    };
    
    // Actualizar la visualización del orden
    updateOrderDisplay();
}

// Función para generar la lista de documentos
function generateDocumentsList(documents, defaultDocId) {
    let html = '';
    
    documents.forEach(doc => {
        const isDefault = doc.document_id === defaultDocId;
        const isSelected = selectedDocuments.includes(doc.document_id);
        
        html += `
            <div class="document-item" style="border: 1px solid #ddd; padding: 15px; margin: 10px 0; border-radius: 5px; cursor: pointer; transition: all 0.2s ease; ${isSelected ? 'background-color: #e3f2fd; border-color: #2196f3;' : ''}" 
                 data-doc-id="${doc.document_id}" 
                 onclick="toggleDocumentSelection(${doc.document_id}, '${doc.title.replace(/'/g, "\\'")}', ${isDefault})">
                <div style="display: flex; justify-content: between; align-items: center;">
                    <div style="flex-grow: 1;">
                        <div style="font-weight: bold; color: #333;">
                            ${doc.title} ${isDefault ? '(Documento original)' : ''}
                        </div>
                        <div style="color: #666; font-size: 0.9em;">
                            Formato: ${doc.original_format} | Versión: ${doc.version}
                        </div>
                    </div>
                    <div style="margin-left: 10px;">
                        <span class="selection-indicator" style="font-size: 20px;">
                            ${isSelected ? '✅' : '⬜'}
                        </span>
                        ${isSelected && selectedDocuments.indexOf(doc.document_id) !== -1 ? 
                            `<span class="order-number" style="background: #2196f3; color: white; border-radius: 50%; padding: 2px 8px; margin-left: 5px; font-size: 12px;">
                                ${selectedDocuments.indexOf(doc.document_id) + 1}
                            </span>` : ''}
                    </div>
                </div>
            </div>
        `;
    });
    
    return html;
}

// Función para alternar la selección de documentos
function toggleDocumentSelection(docId, title, isDefault) {
    if (isDefault) {
        // El documento por defecto no se puede deseleccionar
        return;
    }
    
    const index = selectedDocuments.indexOf(docId);
    if (index > -1) {
        // Deseleccionar
        selectedDocuments.splice(index, 1);
    } else {
        // Seleccionar
        selectedDocuments.push(docId);
    }
    
    // Actualizar la visualización
    updateDocumentItem(docId);
    updateOrderDisplay();
}

// Función para actualizar la visualización de un elemento de documento
function updateDocumentItem(docId) {
    const docItem = document.querySelector(`[data-doc-id="${docId}"]`);
    if (docItem) {
        const isSelected = selectedDocuments.includes(docId);
        const indicator = docItem.querySelector('.selection-indicator');
        const orderNumber = docItem.querySelector('.order-number');
        
        if (isSelected) {
            docItem.style.backgroundColor = '#e3f2fd';
            docItem.style.borderColor = '#2196f3';
            indicator.textContent = '✅';
            
            // Actualizar número de orden
            if (orderNumber) {
                orderNumber.textContent = selectedDocuments.indexOf(docId) + 1;
            } else {
                const orderSpan = document.createElement('span');
                orderSpan.className = 'order-number';
                orderSpan.style.cssText = 'background: #2196f3; color: white; border-radius: 50%; padding: 2px 8px; margin-left: 5px; font-size: 12px;';
                orderSpan.textContent = selectedDocuments.indexOf(docId) + 1;
                indicator.parentNode.appendChild(orderSpan);
            }
        } else {
            docItem.style.backgroundColor = '';
            docItem.style.borderColor = '#ddd';
            indicator.textContent = '⬜';
            if (orderNumber) {
                orderNumber.remove();
            }
        }
    }
}

// Función para actualizar la visualización del orden
function updateOrderDisplay() {
    const orderList = document.getElementById('orderList');
    if (!orderList) return;
    
    if (selectedDocuments.length === 0) {
        orderList.innerHTML = '<em style="color: #666;">Ningún documento seleccionado</em>';
        return;
    }
    
    // Obtener títulos de los documentos seleccionados
    const orderItems = selectedDocuments.map((docId, index) => {
        const docItem = document.querySelector(`[data-doc-id="${docId}"]`);
        if (docItem) {
            const title = docItem.querySelector('div > div').textContent;
            return `<span style="background: #007bff; color: white; padding: 2px 8px; border-radius: 15px; margin: 2px; display: inline-block; font-size: 12px;">
                        ${index + 1}. ${title}
                    </span>`;
        }
        return '';
    }).join('');
    
    orderList.innerHTML = orderItems;
}

// Función para deseleccionar todos excepto el documento por defecto
function deselectAll() {
    selectedDocuments = [defaultDocumentId]; // Mantener solo el documento por defecto
    
    // Actualizar todas las visualizaciones
    document.querySelectorAll('.document-item').forEach(item => {
        const docId = parseInt(item.dataset.docId);
        updateDocumentItem(docId);
    });
    
    updateOrderDisplay();
}

// Actualizar la función publishSelectedDocuments
function publishSelectedDocuments() {
    console.log('Iniciando publicación...');
    
    if (selectedDocuments.length === 0) {
        alert('Debes seleccionar al menos un documento.');
        return;
    }
    
    // Verificar si se quiere agregar página Home
    const homePageData = getHomePageData();
    if (homePageData === false) {
        // Error en validación, no continuar
        console.log('Error en validación de página Home');
        return;
    }
    
    console.log('Datos de Home Page:', homePageData);
    
    // Cerrar el modal
    const modal = document.getElementById('documentSelectorModal');
    if (modal) {
        modal.remove();
    }
    
    // Crear la URL con los documentos seleccionados en orden
    const documentsParam = selectedDocuments.join(',');
    let url = `/github/login?document_ids=${documentsParam}&publish_type=wiki`;
    
    // Si hay datos de página Home, agregarlos como parámetros
    if (homePageData) {
        console.log('Agregando parámetros de Home Page a URL');
        const homePageParams = new URLSearchParams({
            add_home: 'true',
            organization: homePageData.organization,
            project_title: homePageData.projectTitle,
            context: homePageData.context,
            members: homePageData.members.join('|') // Usar | como separador
        });
        url += `&${homePageParams.toString()}`;
    }
    
    console.log('URL final:', url);
    
    // Redireccionar
    window.location.href = url;
}

// Función simplificada para agregar miembros
function addMember() {
    membersCount++;
    const container = document.getElementById('membersContainer');
    const newInput = document.createElement('input');
    newInput.type = 'text';
    newInput.id = `member${membersCount}`;
    newInput.placeholder = 'Nombre completo del integrante';
    newInput.style.cssText = 'width: 100%; padding: 10px; border: 1px solid #ddd; border-radius: 4px; margin-bottom: 8px;';
    container.appendChild(newInput);
}

// Función simplificada para quitar miembros
function removeMember() {
    if (membersCount > 1) {
        const memberToRemove = document.getElementById(`member${membersCount}`);
        if (memberToRemove) {
            memberToRemove.remove();
            membersCount--;
        }
    } else {
        alert('Debe haber al menos un integrante.');
    }
}

// Función para recopilar datos de la página Home (mejorada)
function getHomePageData() {
    const checkbox = document.getElementById('addHomePageCheck');
    
    if (!checkbox || !checkbox.checked) {
        console.log('Checkbox no marcado, no hay datos de Home');
        return null;
    }
    
    const organizationField = document.getElementById('organizationField');
    const projectTitleField = document.getElementById('projectTitleField');
    const contextField = document.getElementById('contextField');
    
    if (!organizationField || !projectTitleField || !contextField) {
        console.error('Campos de Home no encontrados');
        alert('Error: No se pudieron encontrar los campos de la página Home.');
        return false;
    }
    
    const organization = organizationField.value.trim();
    const projectTitle = projectTitleField.value.trim();
    const context = contextField.value.trim();
    
    // Recopilar integrantes
    const members = [];
    for (let i = 1; i <= membersCount; i++) {
        const memberInput = document.getElementById(`member${i}`);
        if (memberInput && memberInput.value.trim()) {
            members.push(memberInput.value.trim());
        }
    }
    
    console.log('Datos recopilados:', {
        organization,
        projectTitle,
        context,
        members,
        membersCount
    });
    
    // Validar campos requeridos
    const missingFields = [];
    if (!organization) missingFields.push('Organización');
    if (!projectTitle) missingFields.push('Título del Proyecto');
    if (!context) missingFields.push('Contexto');
    if (members.length === 0) missingFields.push('Al menos un Integrante');
    
    if (missingFields.length > 0) {
        alert(`Por favor, completa los siguientes campos de la página Home:\n- ${missingFields.join('\n- ')}`);
        return false;
    }
    
    return {
        organization,
        projectTitle,
        context,
        members
    };
}

// Función para mostrar/ocultar campos de página Home
function toggleHomePageFields() {
    const checkbox = document.getElementById('addHomePageCheck');
    const fields = document.getElementById('homePageFields');
    
    if (checkbox && fields) {
        console.log('Toggle fields, checkbox checked:', checkbox.checked);
        
        if (checkbox.checked) {
            fields.style.display = 'block';
            console.log('Campos mostrados');
        } else {
            fields.style.display = 'none';
            console.log('Campos ocultados');
        }
    } else {
        console.error('Elementos no encontrados:', { checkbox, fields });
    }
}

window.debugModalElements = function() {
    console.log('=== DEBUG MODAL ELEMENTS ===');
    console.log('addHomePageCheck:', document.getElementById('addHomePageCheck'));
    console.log('homePageFields:', document.getElementById('homePageFields'));
    console.log('addMemberBtn:', document.getElementById('addMemberBtn'));
    console.log('removeMemberBtn:', document.getElementById('removeMemberBtn'));
    console.log('publishSelectedBtn:', document.getElementById('publishSelectedBtn'));
    console.log('membersContainer:', document.getElementById('membersContainer'));
    console.log('membersCount:', membersCount);
    console.log('selectedDocuments:', selectedDocuments);
    
    // Verificar todos los campos de miembros
    for (let i = 1; i <= membersCount; i++) {
        console.log(`member${i}:`, document.getElementById(`member${i}`));
    }
};

// Función para testear la recopilación de datos
window.testHomePageData = function() {
    console.log('=== TEST HOME PAGE DATA ===');
    const data = getHomePageData();
    console.log('Resultado:', data);
};

// Función para publicar solo documentos (sin página Home)
function publishOnlyDocuments() {
    if (selectedDocuments.length === 0) {
        alert('Debes seleccionar al menos un documento.');
        return;
    }
    
    // Cerrar modal
    document.getElementById('documentSelectorModal').remove();
    
    // Redireccionar directamente
    const documentsParam = selectedDocuments.join(',');
    window.location.href = `/github/login?document_ids=${documentsParam}&publish_type=wiki`;
}

// Función para mostrar el formulario de página Home
function showHomePageForm() {
    if (selectedDocuments.length === 0) {
        alert('Debes seleccionar al menos un documento.');
        return;
    }
    
    // Ocultar botones y mostrar formulario
    const modalBody = document.querySelector('#documentSelectorModal .modal-body');
    modalBody.innerHTML = `
        <div style="text-align: center; margin-bottom: 20px;">
            <h4 style="margin: 0; color: #2196f3;">🏠 Configurar Página Home</h4>
            <p style="margin: 10px 0; color: #666;">Completa la información para crear una página de inicio para tu wiki</p>
        </div>
        
        <div style="background-color: #f8f9fa; padding: 20px; border-radius: 8px; border-left: 4px solid #2196f3;">
            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 15px; margin-bottom: 15px;">
                <div>
                    <label style="display: block; font-weight: bold; margin-bottom: 5px;">🏫 Organización:</label>
                    <input type="text" id="organizationField" placeholder="Nombre de la organización o universidad" style="width: 100%; padding: 10px; border: 1px solid #ddd; border-radius: 4px;">
                </div>
                <div>
                    <label style="display: block; font-weight: bold; margin-bottom: 5px;">📖 Título del Proyecto:</label>
                    <input type="text" id="projectTitleField" placeholder="Título del proyecto" style="width: 100%; padding: 10px; border: 1px solid #ddd; border-radius: 4px;">
                </div>
            </div>
            
            <div style="margin-bottom: 15px;">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                    <label style="font-weight: bold;">👨‍🎓 Integrantes:</label>
                    <div>
                        <button type="button" id="addMemberBtn" class="btn btn-sm btn-outline-success" style="margin-right: 5px;">+ Agregar</button>
                        <button type="button" id="removeMemberBtn" class="btn btn-sm btn-outline-danger">- Quitar</button>
                    </div>
                </div>
                <div id="membersContainer">
                    <input type="text" id="member1" placeholder="Nombre completo del integrante" style="width: 100%; padding: 10px; border: 1px solid #ddd; border-radius: 4px; margin-bottom: 8px;">
                </div>
            </div>
            
            <div style="margin-bottom: 20px;">
                <label style="display: block; font-weight: bold; margin-bottom: 5px;">📝 Contexto:</label>
                <textarea id="contextField" placeholder="Resumen de lo que trata el repositorio" rows="4" style="width: 100%; padding: 10px; border: 1px solid #ddd; border-radius: 4px; resize: vertical;"></textarea>
            </div>
        </div>
        
        <div style="text-align: center; margin-top: 25px;">
            <button id="backToOptionsBtn" class="btn btn-secondary" style="margin-right: 15px; padding: 10px 20px;">
                ← Volver
            </button>
            <button id="publishWithHomeBtn" class="btn btn-success btn-lg" style="padding: 12px 30px;">
                🚀 Publicar Wiki con Home
            </button>
        </div>
    `;
    
    // Reiniciar contador de miembros
    membersCount = 1;
    
    // Nuevos event listeners para el formulario
    document.getElementById('addMemberBtn').onclick = function() {
        addMember();
    };
    
    document.getElementById('removeMemberBtn').onclick = function() {
        removeMember();
    };
    
    document.getElementById('backToOptionsBtn').onclick = function() {
        // Recrear el modal original
        document.getElementById('documentSelectorModal').remove();
        showDocumentSelector(defaultDocumentId);
    };
    
    document.getElementById('publishWithHomeBtn').onclick = function() {
        publishWithHomePage();
    };
}

function publishWithHomePage() {
    console.log('=== INICIANDO PUBLICACIÓN CON HOME ===');
    
    // Validar campos
    const organization = document.getElementById('organizationField').value.trim();
    const projectTitle = document.getElementById('projectTitleField').value.trim();
    const context = document.getElementById('contextField').value.trim();
    
    console.log('Datos del formulario:');
    console.log('- Organización:', organization);
    console.log('- Título:', projectTitle);
    console.log('- Contexto:', context);
    
    // Recopilar integrantes
    const members = [];
    for (let i = 1; i <= membersCount; i++) {
        const memberInput = document.getElementById(`member${i}`);
        if (memberInput && memberInput.value.trim()) {
            members.push(memberInput.value.trim());
            console.log(`- Integrante ${i}:`, memberInput.value.trim());
        }
    }
    
    console.log('Total integrantes:', members.length);
    console.log('Documentos seleccionados:', selectedDocuments);
    
    // Validar que todos los campos estén completos
    const errors = [];
    if (!organization) errors.push('Organización');
    if (!projectTitle) errors.push('Título del Proyecto');
    if (!context) errors.push('Contexto');
    if (members.length === 0) errors.push('Al menos un Integrante');
    
    if (errors.length > 0) {
        alert(`Por favor completa los siguientes campos:\n• ${errors.join('\n• ')}`);
        return;
    }
    
    // Cerrar modal
    document.getElementById('documentSelectorModal').remove();
    
    // Crear URL con parámetros de Home
    const params = new URLSearchParams({
        document_ids: selectedDocuments.join(','),
        publish_type: 'wiki',
        add_home: 'true',
        organization: organization,
        project_title: projectTitle,
        context: context,
        members: members.join('|')
    });
    
    const finalUrl = `/github/login?${params.toString()}`;
    console.log('URL final:', finalUrl);
    console.log('=== FIN DEBUG FRONTEND ===');
    
    window.location.href = finalUrl;
}