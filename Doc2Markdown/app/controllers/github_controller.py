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
from typing import List
from urllib.parse import urlencode, parse_qs
from urllib.parse import unquote
import textwrap

class GitHubController:
# Modificar el método login para manejar add_home
    @staticmethod
    def login(request: Request, document_id: str = None, document_ids: str = None, publish_type: str = "readme", 
            add_home: str = None, organization: str = None, project_title: str = None, 
            context: str = None, members: str = None):
        
        print("=== DEBUG LOGIN ===")
        print(f"document_ids: {document_ids}")
        print(f"add_home: {add_home}")
        print(f"organization: {organization}")
        print(f"project_title: {project_title}")
        print(f"context: {context}")
        print(f"members: {members}")
        print("==================")
        
        if not document_id and not document_ids:
            raise HTTPException(status_code=400, detail="document_id or document_ids required")
        
        if not Config.GITHUB_CLIENT_ID or not Config.GITHUB_CLIENT_SECRET:
            raise HTTPException(status_code=500, detail="GitHub OAuth no configurado correctamente")
        
        scope = "repo"
        
        # Preparar state
        if document_ids:
            state_parts = [document_ids, publish_type, "multiple"]
            
            # Solo agregar datos de home si add_home es true Y todos los campos están presentes
            if add_home == "true" and all([organization, project_title, context, members]):
                home_data = f"{organization}|||{project_title}|||{context}|||{members}"
                state_parts.append(home_data)
                print(f"✅ Home data added to state: {home_data}")
            else:
                print(f"❌ Home data NOT added. add_home={add_home}, fields present: org={bool(organization)}, title={bool(project_title)}, context={bool(context)}, members={bool(members)}")
            
            state_value = "|".join(state_parts)
        else:
            state_value = f"{document_id}|{publish_type}|single"
        
        print(f"Final state: {state_value}")
        
        params = {
            "client_id": Config.GITHUB_CLIENT_ID,
            "redirect_uri": Config.GITHUB_REDIRECT_URI,
            "scope": scope,
            "state": state_value
        }
        auth_url = f"https://github.com/login/oauth/authorize?{urlencode(params)}"
        return RedirectResponse(url=auth_url)
    
    @staticmethod
    async def callback(request: Request, code: str = None, state: str = None):
        print("=== DEBUG CALLBACK ===")
        print(f"State received (raw): {state}")
        
        if not code or not state:
            raise HTTPException(status_code=400, detail="Missing code or state")
        
        # IMPORTANTE: Decodificar URL antes de procesar
        from urllib.parse import unquote
        state_decoded = unquote(state)
        print(f"State decoded: {state_decoded}")
        
        # NUEVO ENFOQUE: Dividir más cuidadosamente
        # El formato esperado es: documents|publish_type|mode|home_data_completo
        # Donde home_data_completo puede contener | internos
        
        # Primero, separar solo los primeros 3 componentes
        parts = state_decoded.split("|", 3)  # Límite a 3 splits = 4 partes máximo
        
        documents_info = parts[0] if len(parts) > 0 else ""
        publish_type = parts[1] if len(parts) > 1 else "readme"
        mode = parts[2] if len(parts) > 2 else "single"
        home_data_complete = parts[3] if len(parts) > 3 else None
        
        print(f"Documents: {documents_info}")
        print(f"Publish type: {publish_type}")
        print(f"Mode: {mode}")
        print(f"Home data complete: {home_data_complete}")
        
        # Procesar datos de página Home si existen
        home_page_info = None
        if home_data_complete:
            try:
                # Ahora dividir por ||| para obtener los campos de home
                home_parts = home_data_complete.split("|||")
                print(f"Home parts after splitting by |||: {home_parts}")
                
                if len(home_parts) >= 4:
                    # El último campo (members) puede contener | como separador de miembros
                    members_string = home_parts[3]
                    members_list = members_string.split("|") if members_string else []
                    
                    home_page_info = {
                        "organization": home_parts[0],
                        "project_title": home_parts[1], 
                        "context": home_parts[2],
                        "members": members_list
                    }
                    print(f"✅ Home page info processed successfully: {home_page_info}")
                else:
                    print(f"❌ Home data incomplete: expected 4 parts, got {len(home_parts)}: {home_parts}")
            except Exception as e:
                print(f"❌ Error processing home data: {e}")
                import traceback
                traceback.print_exc()
                home_page_info = None
        
        print("=====================")
        
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
                print(f"Token error: {token_data}")
                raise HTTPException(status_code=400, detail=f"Failed to get access token: {token_data}")
            
            # Obtener repos del usuario
            repos_response = await client.get(
                "https://api.github.com/user/repos",
                headers={"Authorization": f"token {access_token}"},
                params={"type": "owner", "sort": "updated"}
            )
            repos = repos_response.json()
            
            # Filtrar repos según el tipo de publicación
            if publish_type == "wiki":
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
                    {GitHubController._generate_repo_list(repos, documents_info, access_token, user_data, publish_type, mode, home_page_info)}
                </div>
                <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/js/bootstrap.bundle.min.js"></script>
                {GitHubController._generate_javascript(documents_info, access_token, user_data, publish_type, mode, home_page_info)}
            </body>
            </html>
            """
            return HTMLResponse(content=html_content)
    
    @staticmethod
    def _generate_repo_list(repos, documents_info, access_token, user_data, publish_type, mode="single", home_page_info=None):
        if not repos:
            if publish_type == "wiki":
                return f"""
                <div class="no-repos">
                    <h3>😔 No se encontraron repositorios con wikis habilitadas</h3>
                    <p>Para usar esta función, necesitas:</p>
                    <ul>
                        <li>Tener al menos un repositorio público</li>
                        <li>Habilitar las wikis en la configuración del repositorio</li>
                    </ul>
                    <div style="margin-top: 20px;">
                        <a href="https://github.com/new" target="_blank" class="btn btn-primary" style="margin-right: 10px;">Crear nuevo repositorio</a>
                        <a href="/document_conversion" class="btn btn-secondary">🔙 Regresar al inicio</a>
                    </div>
                </div>
                """
            else:
                return f"""
                <div class="no-repos">
                    <h3>😔 No se encontraron repositorios públicos</h3>
                    <p>Asegúrate de tener al menos un repositorio público en tu cuenta de GitHub.</p>
                    <div style="margin-top: 20px;">
                        <a href="https://github.com/new" target="_blank" class="btn btn-primary" style="margin-right: 10px;">Crear nuevo repositorio</a>
                        <a href="/document_conversion" class="btn btn-secondary">🔙 Regresar al inicio</a>
                    </div>
                </div>
                """
        
        # Determinar texto basado en modo y tipo
        if mode == "multiple" and publish_type == "wiki":
            if home_page_info:
                action_text = "documentos y página Home en la wiki"
                upload_button_text = "📚 Subir Documentos y Página Home"
            else:
                action_text = "documentos en la wiki"
                upload_button_text = "📚 Subir Documentos como Wiki"
        elif publish_type == "wiki":
            action_text = "wiki"
            upload_button_text = "📚 Subir como Wiki"
        else:
            action_text = "README.md"
            upload_button_text = "📤 Subir README.md al repositorio seleccionado"
        
        repo_html = f"""
        <div style="margin-bottom: 20px;">
            <a href="/document_conversion" class="btn btn-secondary" style="margin-right: 10px;">
                🔙 Regresar al inicio
            </a>
        </div>
        
        <p>Selecciona el repositorio donde quieres subir tu {action_text}:</p>
        <div class='repo-list'>"""
        
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
        
        repo_html += f"""</div>
        <div class="upload-section" style="margin-top: 20px;">
            <div id="selectedInfo" class="selected-info" style="display: none; margin: 15px 0; padding: 10px; background: #e3f2fd; border-radius: 5px; border-left: 4px solid #2196f3;"></div>
            
            <div style="display: flex; gap: 10px; align-items: center; flex-wrap: wrap;">
                <button id="uploadBtn" class="btn btn-primary" disabled style="padding: 10px 20px;">
                    {upload_button_text}
                </button>
                <a href="/document_conversion" class="btn btn-outline-secondary" style="padding: 10px 20px; text-decoration: none;">
                    🔙 Cancelar y regresar
                </a>
            </div>
            
            <div id="loading" class="loading" style="display: none; margin: 15px 0; text-align: center;">
                <div class="spinner-border" role="status" style="margin-bottom: 10px;">
                    <span class="visually-hidden">Loading...</span>
                </div>
                <p>Subiendo archivo(s)...</p>
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
        .btn-outline-secondary {{
            border: 1px solid #6c757d;
            color: #6c757d;
        }}
        .btn-outline-secondary:hover {{
            background-color: #6c757d;
            color: white;
        }}
        </style>"""
        return repo_html
    
    @staticmethod
    def _generate_javascript(documents_info, access_token, user_data, publish_type, mode="single", home_page_info=None):
        endpoint = "upload-wiki-multiple" if mode == "multiple" and publish_type == "wiki" else ("upload-wiki" if publish_type == "wiki" else "upload-readme")
        
        # Convertir home_page_info a JSON para JavaScript - CON DEBUGGING
        home_page_json = json.dumps(home_page_info) if home_page_info else "null"
        
        print(f"=== DEBUG JAVASCRIPT GENERATION ===")
        print(f"home_page_info received: {home_page_info}")
        print(f"home_page_json: {home_page_json}")
        print("===================================")
        
        return f"""
        <script>
        console.log('JavaScript cargado'); // Debug
        let selectedRepo = null;
        const uploadBtn = document.getElementById('uploadBtn');
        const documentsInfo = '{documents_info}';
        const accessToken = '{access_token}';
        const githubUser = {json.dumps(user_data)};
        const publishType = '{publish_type}';
        const mode = '{mode}';
        const homePageInfo = {home_page_json};
        
        console.log('=== DEBUG JAVASCRIPT VARS ===');
        console.log('homePageInfo:', homePageInfo);
        console.log('mode:', mode);
        console.log('publishType:', publishType);
        console.log('=============================');
        
        // Agregar event listeners cuando el DOM esté listo
        document.addEventListener('DOMContentLoaded', function() {{
            console.log('DOM Ready - Agregando event listeners');
            document.querySelectorAll('.repo-item').forEach((item, index) => {{
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
                    if (mode === 'multiple') {{
                        formData.append('document_ids', documentsInfo);
                        
                        // AQUÍ ESTÁ EL FIX: Agregar home page data si existe
                        if (homePageInfo && homePageInfo !== null) {{
                            console.log('✅ Adding home page data to form:', homePageInfo);
                            formData.append('home_page_data', JSON.stringify(homePageInfo));
                        }} else {{
                            console.log('❌ No home page data to add');
                        }}
                    }} else {{
                        formData.append('document_id', documentsInfo);
                    }}
                    formData.append('repo_name', selectedRepo);
                    formData.append('access_token', accessToken);
                    formData.append('github_user', JSON.stringify(githubUser));
                    
                    console.log('Enviando datos:', {{
                        documents_info: documentsInfo,
                        repo_name: selectedRepo,
                        endpoint: '/github/{endpoint}',
                        mode: mode,
                        homePageInfo: homePageInfo
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
                        result.innerHTML = '<h4>✅ ' + data.message + '</h4>' +
                        '<p><a href="' + data.repo_url + '" target="_blank" class="btn btn-success" style="margin-right: 10px;">📖 Ver repositorio en GitHub</a>' +
                        '<a href="/document_conversion" class="btn btn-primary">🏠 Regresar al inicio</a></p>';
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


    @staticmethod
    async def upload_wiki_multiple(
        document_ids: str = Form(...),
        repo_name: str = Form(...),
        access_token: str = Form(...),
        github_user: str = Form(...),
        home_page_data: str = Form(None),
        db: Session = Depends(get_db)
    ):
        print("=== DEBUG UPLOAD MULTIPLE ===")
        print(f"document_ids: {document_ids}")
        print(f"repo_name: {repo_name}")
        print(f"home_page_data: {home_page_data}")
        
        if not all([document_ids, repo_name, access_token, github_user]):
            raise HTTPException(status_code=400, detail="Missing required data")
        
        github_user_data = json.loads(github_user)
        username = github_user_data.get("login")
        
        # Procesar datos de página Home si existen
        home_data = None
        if home_page_data and home_page_data.strip() and home_page_data != "null":
            try:
                home_data = json.loads(home_page_data)
                print(f"✅ Home data parsed successfully: {home_data}")
            except Exception as e:
                print(f"❌ Error parsing home data: {e}")
                print(f"Raw home_page_data: {repr(home_page_data)}")
                home_data = None
        else:
            print(f"❌ No home page data or null: {repr(home_page_data)}")
        
        # Convertir string de IDs a lista de enteros
        doc_ids = [int(doc_id.strip()) for doc_id in document_ids.split(',')]
        print(f"Document IDs: {doc_ids}")
        
        # Obtener documentos
        documents = db.query(Document).filter(Document.document_id.in_(doc_ids)).all()
        if not documents:
            raise HTTPException(status_code=404, detail="Documents not found")
        
        print(f"Found {len(documents)} documents")
        
        # Ordenar documentos según el orden de los IDs
        documents_ordered = []
        for doc_id in doc_ids:
            for doc in documents:
                if doc.document_id == doc_id:
                    documents_ordered.append(doc)
                    print(f"Added document: {doc.title}")
                    break
        
        temp_dir = None
        wiki_dir = None
        
        try:
            # Crear directorio temporal
            temp_dir = tempfile.mkdtemp(prefix="githubwiki_")
            wiki_url = f"https://{access_token}@github.com/{username}/{repo_name}.wiki.git"
            wiki_dir = os.path.join(temp_dir, "wiki")
            original_cwd = os.getcwd()
            
            print(f"Temporary directory: {temp_dir}")
            print(f"Wiki URL: {wiki_url}")
            
            try:
                # Clonar wiki existente
                result = subprocess.run([
                    "git", "clone", wiki_url, wiki_dir
                ], check=True, capture_output=True, text=True, cwd=temp_dir)
                print(f"✅ Wiki cloned successfully")
            except subprocess.CalledProcessError as e:
                print(f"⚠️ Wiki doesn't exist, creating new one")
                # Crear nuevo wiki
                os.makedirs(wiki_dir, exist_ok=True)
                os.chdir(wiki_dir)
                subprocess.run(["git", "init"], check=True, capture_output=True)
                subprocess.run(["git", "remote", "add", "origin", wiki_url], check=True, capture_output=True)
                os.chdir(original_cwd)
            
            os.chdir(wiki_dir)
            print(f"Changed to wiki directory: {os.getcwd()}")
            
            # Configurar git
            user_email = github_user_data.get("email") or "noreply@github.com"
            user_name = github_user_data.get("name") or github_user_data.get("login", "Unknown")
            subprocess.run(["git", "config", "user.email", user_email], check=True, capture_output=True)
            subprocess.run(["git", "config", "user.name", user_name], check=True, capture_output=True)
            
            uploaded_files = []
            
            # Crear página Home SOLO si hay datos
            if home_data:
                print(f"🏠 Creating Home page with data: {home_data}")
                home_content = GitHubController._generate_home_page_content(home_data, documents_ordered)
                print(f"Generated home content:\n{home_content}")
                
                with open("Home.md", "w", encoding="utf-8") as f:
                    f.write(home_content)
                subprocess.run(["git", "add", "Home.md"], check=True, capture_output=True)
                uploaded_files.append("Home.md")
                print("✅ Home.md created and added to git")
            else:
                print("❌ No home data, skipping Home.md creation")
            
            # Procesar documentos
            for document in documents_ordered:
                # Mantener paréntesis y otros caracteres permitidos en GitHub wiki
                wiki_filename = document.title.replace(" ", "-").replace("/", "-")
                # Permitir paréntesis, guiones, guiones bajos y caracteres alfanuméricos
                wiki_filename = "".join(c for c in wiki_filename if c.isalnum() or c in ('-', '_', '(', ')')).rstrip()
                wiki_filename = f"{wiki_filename}.md"
                
                print(f"📄 Creating document: {document.title} -> {wiki_filename}")
                
                with open(wiki_filename, "w", encoding="utf-8") as f:
                    f.write(document.markdown_content)
                
                subprocess.run(["git", "add", wiki_filename], check=True, capture_output=True)
                uploaded_files.append(wiki_filename)
            
            # Commit
            if home_data:
                commit_message = f"Wiki complete: Home page and {len(documents_ordered)} documents"
                success_message = f"Wiki completa publicada: página Home y {len(documents_ordered)} documentos en {username}/{repo_name}"
            else:
                commit_message = f"Add/Update {len(documents_ordered)} wiki documents"
                success_message = f"{len(documents_ordered)} documentos publicados exitosamente en {username}/{repo_name}"
            
            print(f"📝 Committing with message: {commit_message}")
            subprocess.run(["git", "commit", "-m", commit_message], check=True, capture_output=True)
            
            # Push
            print("📤 Pushing to GitHub...")
            push_result = subprocess.run(["git", "push", "origin", "master"], check=True, capture_output=True, text=True)
            print(f"✅ Push successful: {push_result.stdout}")
            
            os.chdir(original_cwd)
            GitHubController._safe_cleanup_directory(temp_dir)
            
            print(f"🎉 Upload completed successfully!")
            print(f"Files uploaded: {uploaded_files}")
            print("===============================")
            
            return {
                "success": True,
                "message": success_message,
                "repo_url": f"https://github.com/{username}/{repo_name}/wiki",
                "uploaded_files": uploaded_files
            }
        
        except Exception as e:
            print(f"❌ Error during upload: {str(e)}")
            import traceback
            traceback.print_exc()
            
            try:
                os.chdir(original_cwd)
            except:
                pass
            if temp_dir and os.path.exists(temp_dir):
                GitHubController._safe_cleanup_directory(temp_dir)
            
            return {
                "success": False,
                "error": f"Error: {str(e)}"
            }

    # Nuevo método para generar el contenido de la página Home
    @staticmethod
    def _generate_home_page_content(home_data, documents):
        """
        Genera el contenido de la página Home basado en la plantilla exacta
        """
        organization = home_data.get("organization", "")
        project_title = home_data.get("project_title", "")
        context = home_data.get("context", "")
        members = home_data.get("members", [])
        
        print(f"🏠 Generating home page content:")
        print(f"  Organization: {organization}")
        print(f"  Project title: {project_title}")
        print(f"  Context: {context}")
        print(f"  Members: {members}")
        
        # Generar lista de integrantes (SIN espacios extra al inicio)
        members_list = "\n".join([f"- {member}" for member in members])
        
        # Generar índice de documentos con nombres correctos (incluyendo paréntesis)
        documents_index_items = []
        for doc in documents:
            # Usar la misma lógica de generación de nombres que en upload_wiki_multiple
            wiki_link_name = doc.title.replace(" ", "-").replace("/", "-")
            wiki_link_name = "".join(c for c in wiki_link_name if c.isalnum() or c in ('-', '_', '(', ')')).rstrip()
            documents_index_items.append(f"- 📖 [{doc.title}]({wiki_link_name})")
        
        documents_index = "\n".join(documents_index_items)
        
        # Construir el contenido línea por línea para evitar problemas de indentación
        lines = [
            f"# 🏫 {organization}",
            "## 👨‍🎓 Integrantes:",
            members_list,
            "---",
            f"# 🚀 Proyecto: {project_title}",
            "---",
            "## 📚 Contexto",
            context,
            "---",
            "## 📌 ¿Qué encontrarás en esta Wiki?",
            documents_index
        ]
        
        home_content = "\n".join(lines)
        
        print(f"Generated content:\n{home_content}")
        return home_content