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
import tempfile
import os
import subprocess
import shutil
import time
import gc

class GitHubController:
    @staticmethod
    def login(request: Request, document_id: str, publish_type: str = "readme"):
        if not document_id:
            raise HTTPException(status_code=400, detail="document_id required")
        
        # Debug: Verificar configuración
        print(f"GITHUB_CLIENT_ID: {Config.GITHUB_CLIENT_ID}")
        print(f"GITHUB_REDIRECT_URI: {Config.GITHUB_REDIRECT_URI}")
        
        if not Config.GITHUB_CLIENT_ID or not Config.GITHUB_CLIENT_SECRET:
            raise HTTPException(status_code=500, detail="GitHub OAuth no configurado correctamente")
        
        # Definir scopes según el tipo de publicación
        if publish_type == "wiki":
            scope = "repo"  # Para wikis necesitamos acceso completo al repo
        else:
            scope = "repo"  # Para README también necesitamos repo
        
        # Generar URL de autorización
        params = {
            "client_id": Config.GITHUB_CLIENT_ID,
            "redirect_uri": Config.GITHUB_REDIRECT_URI,
            "scope": scope,
            "state": f"{document_id}|{publish_type}"  # Incluimos el tipo de publicación
        }
        auth_url = f"https://github.com/login/oauth/authorize?{urlencode(params)}"
        print(f"Auth URL: {auth_url}")  # Debug
        return RedirectResponse(url=auth_url)
    
    @staticmethod
    async def callback(request: Request, code: str = None, state: str = None):
        if not code or not state:
            raise HTTPException(status_code=400, detail="Missing code or document_id")
        
        # Extraer document_id y publish_type del state
        state_parts = state.split("|")
        document_id = state_parts[0]
        publish_type = state_parts[1] if len(state_parts) > 1 else "readme"
        
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
            
            # Para wikis, necesitamos repos que tengan wikis habilitadas
            if publish_type == "wiki":
                # Filtrar repos que tengan wikis habilitadas
                wiki_enabled_repos = []
                for repo in repos:
                    if not repo.get("private", True) and repo.get("has_wiki", False):
                        wiki_enabled_repos.append(repo)
                repos = wiki_enabled_repos
            else:
                public_repos = [repo for repo in repos if not repo.get("private", True)]
                repos = public_repos
            
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
                    {GitHubController._generate_repo_list(repos, document_id, access_token, user_data, publish_type)}
                </div>
                <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/js/bootstrap.bundle.min.js"></script>
                {GitHubController._generate_javascript(document_id, access_token, user_data, publish_type)}
            </body>
            </html>
            """
            return HTMLResponse(content=html_content)
    
    @staticmethod
    def _generate_repo_list(repos, document_id, access_token, user_data, publish_type):
        if not repos:
            if publish_type == "wiki":
                return """
                <div class="no-repos">
                    <h3>😔 No se encontraron repositorios con wikis habilitadas</h3>
                    <p>Para usar esta función, necesitas:</p>
                    <ul>
                        <li>Tener al menos un repositorio público</li>
                        <li>Habilitar las wikis en la configuración del repositorio</li>
                    </ul>
                    <a href="https://github.com/new" target="_blank" class="btn btn-primary">Crear nuevo repositorio</a>
                </div>
                """
            else:
                return """
                <div class="no-repos">
                    <h3>😔 No se encontraron repositorios públicos</h3>
                    <p>Asegúrate de tener al menos un repositorio público en tu cuenta de GitHub.</p>
                    <a href="https://github.com/new" target="_blank" class="btn btn-primary">Crear nuevo repositorio</a>
                </div>
                """
        
        action_text = "wiki" if publish_type == "wiki" else "README.md"
        repo_html = f"<p>Selecciona el repositorio donde quieres subir tu {action_text}:</p><div class='repo-list'>"
        
        for i, repo in enumerate(repos):
            wiki_indicator = "📚 Wiki habilitada" if publish_type == "wiki" and repo.get('has_wiki') else ""
            repo_html += f"""
            <div class="repo-item" 
                 data-repo="{repo['name']}" 
                 style="border: 1px solid #ddd; padding: 15px; margin: 10px 0; cursor: pointer; border-radius: 5px; transition: all 0.2s ease;"
                 onmouseover="this.style.backgroundColor='#f8f9fa'"
                 onmouseout="this.style.backgroundColor='white'">
                <div class="repo-name"><strong>{repo['name']}</strong> {wiki_indicator}</div>
                {f"<div class='repo-description'>{repo['description']}</div>" if repo.get('description') else ""}
                <div class="repo-meta" style="color: #666; font-size: 0.9em; margin-top: 8px;">
                    ⭐ {repo['stargazers_count']} | 
                    🍴 {repo['forks_count']} | 
                    📅 Actualizado: {repo['updated_at'][:10]}
                </div>
            </div>
            """
        
        upload_button_text = "📚 Subir como Wiki" if publish_type == "wiki" else "📤 Subir README.md al repositorio seleccionado"
        
        repo_html += f"""</div>
        <div class="upload-section" style="margin-top: 20px;">
            <div id="selectedInfo" class="selected-info" style="display: none; margin: 15px 0; padding: 10px; background: #e3f2fd; border-radius: 5px; border-left: 4px solid #2196f3;"></div>
            <button id="uploadBtn" class="btn btn-primary" disabled style="padding: 10px 20px;">
                {upload_button_text}
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
        .repo-item:hover {{
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        }}
        .repo-item.selected {{
            border: 2px solid #007bff !important;
            background-color: #f0f8ff !important;
        }}
        </style>"""
        return repo_html
    
    @staticmethod
    def _generate_javascript(document_id, access_token, user_data, publish_type):
        endpoint = "upload-wiki" if publish_type == "wiki" else "upload-readme"
        
        return f"""
        <script>
        console.log('JavaScript cargado'); // Debug
        let selectedRepo = null;
        const uploadBtn = document.getElementById('uploadBtn');
        const documentId = '{document_id}';
        const accessToken = '{access_token}';
        const githubUser = {json.dumps(user_data)};
        const publishType = '{publish_type}';
        
        console.log('Elementos encontrados:', {{
            uploadBtn: uploadBtn,
            repoItems: document.querySelectorAll('.repo-item').length,
            publishType: publishType
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
                        repo_name: selectedRepo,
                        endpoint: '/github/{endpoint}'
                    }});
                    
                    const response = await fetch('/github/{endpoint}', {{
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
    
    @staticmethod
    def _safe_cleanup_directory(directory_path, max_retries=5, delay=1):
        """
        Función para limpiar directorios de forma segura en Windows
        """
        for attempt in range(max_retries):
            try:
                if os.path.exists(directory_path):
                    # Intentar cambiar permisos de archivos antes de eliminar
                    for root, dirs, files in os.walk(directory_path):
                        for file in files:
                            try:
                                os.chmod(os.path.join(root, file), 0o777)
                            except:
                                pass
                    
                    # Forzar garbage collection
                    gc.collect()
                    
                    # Intentar eliminar
                    shutil.rmtree(directory_path, ignore_errors=True)
                    
                    # Verificar si se eliminó
                    if not os.path.exists(directory_path):
                        return True
                        
            except Exception as e:
                print(f"Intento {attempt + 1} fallido: {e}")
                
            if attempt < max_retries - 1:
                time.sleep(delay * (attempt + 1))
        
        return False
    
    @staticmethod
    async def upload_wiki(
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
        
        username = github_user_data.get("login")
        temp_dir = None
        wiki_dir = None
        
        try:
            # Crear directorio temporal personalizado
            temp_dir = tempfile.mkdtemp(prefix="github_wiki_")
            wiki_url = f"https://{access_token}@github.com/{username}/{repo_name}.wiki.git"
            wiki_dir = os.path.join(temp_dir, "wiki")
            
            # Variables para controlar el directorio de trabajo
            original_cwd = os.getcwd()
            
            try:
                # Intentar clonar el wiki existente
                result = subprocess.run([
                    "git", "clone", wiki_url, wiki_dir
                ], check=True, capture_output=True, text=True, cwd=temp_dir)
                print(f"Wiki clonado exitosamente: {result.stdout}")
            except subprocess.CalledProcessError as e:
                print(f"Wiki no existe, creando nuevo: {e.stderr}")
                # Si el wiki no existe, inicializar uno nuevo
                os.makedirs(wiki_dir, exist_ok=True)
                os.chdir(wiki_dir)
                
                subprocess.run(["git", "init"], check=True, capture_output=True)
                subprocess.run(["git", "remote", "add", "origin", wiki_url], check=True, capture_output=True)
                
                # Cambiar de vuelta al directorio original
                os.chdir(original_cwd)
            
            # Cambiar al directorio wiki para trabajar
            os.chdir(wiki_dir)
            
            # Crear el archivo de la wiki
            wiki_filename = document.title.replace(" ", "-").replace("/", "-")
            # Remover caracteres especiales problemáticos
            wiki_filename = "".join(c for c in wiki_filename if c.isalnum() or c in ('-', '_')).rstrip()
            wiki_filename = f"{wiki_filename}.md"
            
            # Escribir el contenido
            with open(wiki_filename, "w", encoding="utf-8") as f:
                f.write(document.markdown_content)
            
            # Configurar git (necesario para commits)
            user_email = github_user_data.get("email") or "noreply@github.com"
            user_name = github_user_data.get("name") or github_user_data.get("login", "Unknown")
            
            subprocess.run([
                "git", "config", "user.email", user_email
            ], check=True, capture_output=True)
            subprocess.run([
                "git", "config", "user.name", user_name
            ], check=True, capture_output=True)
            
            # Agregar y hacer commit
            subprocess.run(["git", "add", wiki_filename], check=True, capture_output=True)
            subprocess.run([
                "git", "commit", "-m", f"Add/Update wiki page: {document.title}"
            ], check=True, capture_output=True)
            
            # Push al repositorio wiki
            push_result = subprocess.run([
                "git", "push", "origin", "master"
            ], check=True, capture_output=True, text=True)
            
            print(f"Push exitoso: {push_result.stdout}")
            
            # Cambiar de vuelta al directorio original antes de limpiar
            os.chdir(original_cwd)
            
            # Intentar limpiar el directorio temporal
            cleanup_success = GitHubController._safe_cleanup_directory(temp_dir)
            if not cleanup_success:
                print(f"Advertencia: No se pudo limpiar completamente el directorio temporal: {temp_dir}")
            
            return {
                "success": True,
                "message": f"Wiki '{document.title}' publicada exitosamente en {username}/{repo_name}",
                "repo_url": f"https://github.com/{username}/{repo_name}/wiki/{wiki_filename.replace('.md', '')}"
            }
            
        except subprocess.CalledProcessError as e:
            error_msg = e.stderr if hasattr(e, 'stderr') and e.stderr else str(e)
            print(f"Error en subprocess: {error_msg}")
            return {
                "success": False,
                "error": f"Error al crear la wiki: {error_msg}"
            }
        except Exception as e:
            print(f"Error inesperado: {str(e)}")
            return {
                "success": False,
                "error": f"Error inesperado: {str(e)}"
            }
        finally:
            # Asegurar que volvemos al directorio original
            try:
                os.chdir(original_cwd)
            except:
                pass
            
            # Intento final de limpieza si no se hizo antes
            if temp_dir and os.path.exists(temp_dir):
                GitHubController._safe_cleanup_directory(temp_dir)