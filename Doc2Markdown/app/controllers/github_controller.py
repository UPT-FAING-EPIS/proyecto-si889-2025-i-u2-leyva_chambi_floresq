from fastapi import Request, HTTPException, Form, Depends
from fastapi.responses import RedirectResponse, HTMLResponse
from sqlalchemy.orm import Session
import httpx
import base64
import json
from urllib.parse import urlencode
from config.config import Config
from config.database import get_db
from app.models.document_model import Document

class GitHubController:
    @staticmethod
    def login(request: Request, document_id: str):
        if not document_id:
            raise HTTPException(status_code=400, detail="document_id required")
        
        # Debug: Verificar configuración
        print(f"GITHUB_CLIENT_ID: {Config.GITHUB_CLIENT_ID}")
        print(f"GITHUB_REDIRECT_URI: {Config.GITHUB_REDIRECT_URI}")
        
        if not Config.GITHUB_CLIENT_ID or not Config.GITHUB_CLIENT_SECRET:
            raise HTTPException(status_code=500, detail="GitHub OAuth no configurado correctamente")
        
        # Generar URL de autorización
        params = {
            "client_id": Config.GITHUB_CLIENT_ID,
            "redirect_uri": Config.GITHUB_REDIRECT_URI,
            "scope": "repo",
            "state": document_id  # Usamos state para pasar el document_id
        }
        auth_url = f"https://github.com/login/oauth/authorize?{urlencode(params)}"
        print(f"Auth URL: {auth_url}")  # Debug
        return RedirectResponse(url=auth_url)
    
    @staticmethod
    async def callback(request: Request, code: str = None, state: str = None):
        if not code or not state:
            raise HTTPException(status_code=400, detail="Missing code or document_id")
        
        document_id = state
        
        # Intercambiar código por token
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://github.com/login/oauth/access_token",
                data={
                    "client_id": Config.GITHUB_CLIENT_ID,
                    "client_secret": Config.GITHUB_CLIENT_SECRET,
                    "code": code,
                    "redirect_uri": Config.GITHUB_REDIRECT_URI
                },
                headers={"Accept": "application/json"}
            )
            token_data = response.json()
            access_token = token_data.get("access_token")
            
            if not access_token:
                print(f"Token error: {token_data}")  # Debug
                raise HTTPException(status_code=400, detail=f"Failed to get access token: {token_data}")
            
            # Obtener repos del usuario
            repos_response = await client.get(
                "https://api.github.com/user/repos",
                headers={"Authorization": f"token {access_token}"},
                params={"type": "owner", "sort": "updated"}
            )
            repos = repos_response.json()
            public_repos = [repo for repo in repos if not repo.get("private", True)]
            
            # Obtener info del usuario
            user_response = await client.get(
                "https://api.github.com/user",
                headers={"Authorization": f"token {access_token}"}
            )
            user_data = user_response.json()
            
            # Crear HTML response
            html_content = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <title>Seleccionar Repositorio</title>
                <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
            </head>
            <body>
                <div class="container mt-4">
                    <h1>📂 Selecciona un Repositorio</h1>
                    {GitHubController._generate_repo_list(public_repos, document_id, access_token, user_data)}
                </div>
                <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/js/bootstrap.bundle.min.js"></script>
                {GitHubController._generate_javascript(document_id, access_token, user_data)}
            </body>
            </html>
            """
            return HTMLResponse(content=html_content)
    
    @staticmethod
    def _generate_repo_list(repos, document_id, access_token, user_data):
        if not repos:
            return """
            <div class="no-repos">
                <h3>😔 No se encontraron repositorios públicos</h3>
                <p>Asegúrate de tener al menos un repositorio público en tu cuenta de GitHub.</p>
                <a href="https://github.com/new" target="_blank" class="btn btn-primary">Crear nuevo repositorio</a>
            </div>
            """
        
        repo_html = "<p>Selecciona el repositorio público donde quieres subir tu README.md:</p><div class='repo-list'>"
        for i, repo in enumerate(repos):
            repo_html += f"""
            <div class="repo-item" 
                 data-repo="{repo['name']}" 
                 style="border: 1px solid #ddd; padding: 15px; margin: 10px 0; cursor: pointer; border-radius: 5px; transition: all 0.2s ease;"
                 onmouseover="this.style.backgroundColor='#f8f9fa'"
                 onmouseout="this.style.backgroundColor='white'">
                <div class="repo-name"><strong>{repo['name']}</strong></div>
                {f"<div class='repo-description'>{repo['description']}</div>" if repo.get('description') else ""}
                <div class="repo-meta" style="color: #666; font-size: 0.9em; margin-top: 8px;">
                    ⭐ {repo['stargazers_count']} | 
                    🍴 {repo['forks_count']} | 
                    📅 Actualizado: {repo['updated_at'][:10]}
                </div>
            </div>
            """
        
        repo_html += """</div>
        <div class="upload-section" style="margin-top: 20px;">
            <div id="selectedInfo" class="selected-info" style="display: none; margin: 15px 0; padding: 10px; background: #e3f2fd; border-radius: 5px; border-left: 4px solid #2196f3;"></div>
            <button id="uploadBtn" class="btn btn-primary" disabled style="padding: 10px 20px;">
                📤 Subir README.md al repositorio seleccionado
            </button>
            <div id="loading" class="loading" style="display: none; margin: 15px 0; text-align: center;">
                <div class="spinner-border" role="status" style="margin-bottom: 10px;">
                    <span class="visually-hidden">Loading...</span>
                </div>
                <p>Subiendo archivo...</p>
            </div>
            <div id="result" class="result" style="margin-top: 15px;"></div>
        </div>
        
        <style>
        .repo-item:hover {
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        }
        .repo-item.selected {
            border: 2px solid #007bff !important;
            background-color: #f0f8ff !important;
        }
        </style>"""
        return repo_html
    
    @staticmethod
    def _generate_javascript(document_id, access_token, user_data):
        # Escapar datos para JavaScript
        user_data_json = json.dumps(user_data).replace('"', '\\"')
        
        return f"""
        <script>
        console.log('JavaScript cargado'); // Debug
        let selectedRepo = null;
        const uploadBtn = document.getElementById('uploadBtn');
        const documentId = '{document_id}';
        const accessToken = '{access_token}';
        const githubUser = {json.dumps(user_data)};
        
        console.log('Elementos encontrados:', {{
            uploadBtn: uploadBtn,
            repoItems: document.querySelectorAll('.repo-item').length
        }});
        
        // Agregar event listeners cuando el DOM esté listo
        document.addEventListener('DOMContentLoaded', function() {{
            console.log('DOM Ready - Agregando event listeners');
            
            document.querySelectorAll('.repo-item').forEach((item, index) => {{
                console.log('Agregando listener al repo', index, item.dataset.repo);
                item.addEventListener('click', function() {{
                    console.log('Repo clickeado:', this.dataset.repo);
                    document.querySelectorAll('.repo-item').forEach(i => i.style.border = '1px solid #ddd');
                    this.style.border = '2px solid #007bff';
                    selectedRepo = this.dataset.repo;
                    const selectedInfo = document.getElementById('selectedInfo');
                    selectedInfo.innerHTML = '📁 Repositorio seleccionado: <strong>' + selectedRepo + '</strong>';
                    selectedInfo.style.display = 'block';
                    uploadBtn.disabled = false;
                    console.log('Repositorio seleccionado:', selectedRepo);
                }});
            }});
            
            uploadBtn.addEventListener('click', async function() {{
                console.log('Upload button clicked, selectedRepo:', selectedRepo);
                if (!selectedRepo) return;
                
                const loading = document.getElementById('loading');
                const result = document.getElementById('result');
                loading.style.display = 'block';
                uploadBtn.disabled = true;
                result.style.display = 'none';
                
                try {{
                    const formData = new FormData();
                    formData.append('document_id', documentId);
                    formData.append('repo_name', selectedRepo);
                    formData.append('access_token', accessToken);
                    formData.append('github_user', JSON.stringify(githubUser));
                    
                    console.log('Enviando datos:', {{
                        document_id: documentId,
                        repo_name: selectedRepo
                    }});
                    
                    const response = await fetch('/github/upload-readme', {{
                        method: 'POST',
                        body: formData
                    }});
                    
                    const data = await response.json();
                    console.log('Respuesta recibida:', data);
                    
                    loading.style.display = 'none';
                    result.style.display = 'block';
                    
                    if (data.success) {{
                        result.className = 'alert alert-success';
                        result.innerHTML = '<h4>✅ ' + data.message + '</h4><p><a href="' + data.repo_url + '" target="_blank">Ver repositorio en GitHub</a></p>';
                    }} else {{
                        result.className = 'alert alert-danger';
                        result.innerHTML = '<h4>❌ Error</h4><p>' + data.error + '</p>';
                        uploadBtn.disabled = false;
                    }}
                }} catch (error) {{
                    console.error('Error en upload:', error);
                    loading.style.display = 'none';
                    result.style.display = 'block';
                    result.className = 'alert alert-danger';
                    result.innerHTML = '<h4>❌ Error</h4><p>Error de conexión: ' + error.message + '</p>';
                    uploadBtn.disabled = false;
                }}
            }});
        }});
        
        // También agregar los listeners inmediatamente por si acaso
        setTimeout(function() {{
            console.log('Timeout - Agregando event listeners como backup');
            document.querySelectorAll('.repo-item').forEach((item, index) => {{
                if (!item.hasAttribute('data-listener-added')) {{
                    item.setAttribute('data-listener-added', 'true');
                    item.addEventListener('click', function() {{
                        console.log('Repo clickeado (backup):', this.dataset.repo);
                        document.querySelectorAll('.repo-item').forEach(i => i.style.border = '1px solid #ddd');
                        this.style.border = '2px solid #007bff';
                        selectedRepo = this.dataset.repo;
                        const selectedInfo = document.getElementById('selectedInfo');
                        selectedInfo.innerHTML = '📁 Repositorio seleccionado: <strong>' + selectedRepo + '</strong>';
                        selectedInfo.style.display = 'block';
                        uploadBtn.disabled = false;
                    }});
                }}
            }});
        }}, 500);
        </script>
        """
    
    @staticmethod
    async def upload_readme(
        document_id: str = Form(...),
        repo_name: str = Form(...),
        access_token: str = Form(...),
        github_user: str = Form(...),
        db: Session = Depends(get_db)
    ):
        if not all([document_id, repo_name, access_token, github_user]):
            raise HTTPException(status_code=400, detail="Missing required data")
        
        github_user_data = json.loads(github_user)
        
        # Obtener documento usando SQLAlchemy ORM
        document = db.query(Document).filter(
            Document.document_id == int(document_id)
        ).first()
        
        if not document:
            raise HTTPException(status_code=404, detail="Document not found")
        
        # Subir a GitHub
        username = github_user_data.get("login")
        content_base64 = base64.b64encode(document.markdown_content.encode('utf-8')).decode('utf-8')
        
        async with httpx.AsyncClient() as client:
            readme_url = f"https://api.github.com/repos/{username}/{repo_name}/contents/README.md"
            
            # Verificar si README existe
            readme_response = await client.get(
                readme_url,
                headers={"Authorization": f"token {access_token}"}
            )
            
            commit_data = {
                "message": f"Update README.md: {document.title}",
                "content": content_base64
            }
            
            if readme_response.status_code == 200:
                existing_readme = readme_response.json()
                commit_data["sha"] = existing_readme["sha"]
                action = "actualizado"
            else:
                action = "creado"
            
            # Subir archivo
            upload_response = await client.put(
                readme_url,
                json=commit_data,
                headers={"Authorization": f"token {access_token}"}
            )
            
            if upload_response.status_code in [200, 201]:
                return {
                    "success": True,
                    "message": f"README.md {action} exitosamente en {username}/{repo_name}",
                    "repo_url": f"https://github.com/{username}/{repo_name}"
                }
            else:
                return {
                    "success": False,
                    "error": f"Error al subir archivo: {upload_response.text}"
                }