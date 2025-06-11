import re
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from typing import List, Dict, Any
import numpy as np

class PlagiarismDetector:
    def __init__(self):
        self.spanish_stopwords = {
            'el', 'la', 'de', 'que', 'y', 'a', 'en', 'un', 'es', 'se', 'no', 'te', 'lo', 'le',
            'da', 'su', 'por', 'son', 'con', 'para', 'al', 'del', 'los', 'las', 'una', 'como',
            'pero', 'sus', 'le', 'ya', 'o', 'fue', 'este', 'ha', 'si', 'porque', 'esta', 'son',
            'entre', 'cuando', 'muy', 'sin', 'sobre', 'ser', 'tiene', 'también', 'me', 'hasta',
            'hay', 'donde', 'han', 'quien', 'están', 'estado', 'desde', 'todo', 'nos', 'durante',
            'todos', 'uno', 'les', 'ni', 'contra', 'otros', 'fueron', 'ese', 'eso', 'había',
            'ante', 'ellos', 'e', 'esto', 'mí', 'antes', 'algunos', 'qué', 'unos', 'yo', 'otro',
            'otras', 'otra', 'él', 'tanto', 'esa', 'estos', 'mucho', 'quienes', 'nada', 'muchos',
            'cual', 'sea', 'poco', 'ella', 'estar', 'haber', 'estas', 'estaba', 'estamos', 'pueden',
            'hacen', 'cada', 'fin', 'incluido', 'primero', 'además', 'su', 'forma', 'gran', 'con',
            'sentir', 'muy', 'aquí', 'saber', 'has', 'tú', 'te', 'la', 'one', 'su'
        }
    
    def clean_markdown_content(self, text: str) -> str:
        """
        Limpia el contenido markdown según reglas específicas
        """
        if not text:
            return ""
        
        lines = text.split('\n')
        cleaned_lines = []
        
        for line in lines:
            # Eliminar líneas que contengan ciertos caracteres
            if any(char in line for char in ['#', '|', ':', '_', '"', '-']):
                continue
            
            # Eliminar líneas numeradas
            if re.match(r'^\s*\d+\.\s', line):
                continue
            
            # Procesar línea
            processed_line = re.sub(r'`([^`]*)`', '', line)  # Elimina código inline
            processed_line = re.sub(r'\*([^*]*)\*', '', processed_line)  # Elimina texto en asteriscos
            processed_line = re.sub(r'\[([^\]]*)\]', '', processed_line)  # Elimina texto en corchetes
            processed_line = re.sub(r'\(([^)]*)\)', '', processed_line)  # Elimina texto en paréntesis
            processed_line = re.sub(r'<[^>]*>', '', processed_line)  # Elimina HTML tags
            processed_line = re.sub(r'\s+', ' ', processed_line).strip()
            
            if processed_line and not re.match(r'^[\s\*\-=#\[\](){}|<>"~+.,:;!?]*$', processed_line):
                cleaned_lines.append(processed_line)
        
        cleaned_text = '\n'.join(cleaned_lines)
        cleaned_text = re.sub(r'\n\s*\n\s*\n+', '\n\n', cleaned_text)
        return cleaned_text.strip()
    
    def vectorize_texts(self, texts: List[str]) -> np.ndarray:
        """
        Vectoriza una lista de textos usando TF-IDF
        """
        if not texts or all(not text.strip() for text in texts):
            return np.array([])
        
        vectorizer = TfidfVectorizer(
            stop_words=list(self.spanish_stopwords),
            ngram_range=(1, 2),
            min_df=1,
            max_df=0.8,
            lowercase=True,
            token_pattern=r'\b[a-záéíóúüñ]+\b'
        )
        
        try:
            vectors = vectorizer.fit_transform(texts).toarray()
            return vectors
        except Exception as e:
            print(f"Error al vectorizar: {e}")
            return np.array([])
    
    def calculate_similarity(self, doc1_vector, doc2_vector) -> float:
        """
        Calcula la similitud del coseno entre dos vectores
        """
        try:
            # Reshapear los vectores para asegurar que tengan la forma correcta
            vec1 = np.array(doc1_vector).reshape(1, -1)
            vec2 = np.array(doc2_vector).reshape(1, -1)
            
            similarity_matrix = cosine_similarity(vec1, vec2)
            return float(similarity_matrix[0][0])
        except Exception as e:
            print(f"Error al calcular similitud: {e}")
            return 0.0
    
    def classify_similarity(self, similarity_score: float) -> Dict[str, Any]:
        """
        Clasifica el nivel de similitud
        """
        percentage = similarity_score * 100
        
        if similarity_score > 0.7:
            level = "ALTO"
            color = "danger"
            icon = "🔴"
        elif similarity_score > 0.3:
            level = "MEDIO"
            color = "warning"
            icon = "🟡"
        else:
            level = "BAJO"
            color = "success"
            icon = "🟢"
        
        return {
            "level": level,
            "color": color,
            "icon": icon,
            "percentage": round(percentage, 2)
        }
    
    def analyze_similarities(self, documents_data: List[Dict], target_document_id: int) -> List[Dict]:
        """
        Analiza similitudes entre el documento objetivo y los demás
        """
        try:
            # Validar entrada
            if not documents_data:
                return []
            
            # Limpiar contenidos
            cleaned_contents = []
            for doc in documents_data:
                cleaned_content = self.clean_markdown_content(doc.get('content', ''))
                cleaned_contents.append(cleaned_content)
            
            # Filtrar contenidos vacíos
            if not any(content.strip() for content in cleaned_contents):
                return []
            
            # Vectorizar
            vectors = self.vectorize_texts(cleaned_contents)
            
            # Verificar si la vectorización fue exitosa
            if vectors.size == 0:
                print("No se pudieron vectorizar los textos")
                return []
            
            # Encontrar índice del documento objetivo
            target_index = None
            for i, doc in enumerate(documents_data):
                if doc.get('id') == target_document_id:
                    target_index = i
                    break
            
            if target_index is None:
                print(f"No se encontró el documento objetivo con ID: {target_document_id}")
                return []
            
            # Verificar que el índice objetivo esté dentro del rango
            if target_index >= len(vectors):
                print(f"Índice objetivo fuera de rango: {target_index}")
                return []
            
            # Calcular similitudes
            results = []
            target_vector = vectors[target_index]
            
            for i, doc in enumerate(documents_data):
                if i == target_index:  # Saltar el documento objetivo
                    continue
                
                if i >= len(vectors):  # Verificar que el índice esté dentro del rango
                    continue
                
                similarity_score = self.calculate_similarity(target_vector, vectors[i])
                classification = self.classify_similarity(similarity_score)
                
                results.append({
                    "document_id": doc.get('id'),
                    "title": doc.get('title', 'Sin título'),
                    "author": doc.get('author', 'Sin autor'),
                    "similarity_score": round(similarity_score, 4),
                    "classification": classification
                })
            
            # Ordenar por similitud descendente
            results.sort(key=lambda x: x['similarity_score'], reverse=True)
            
            return results
            
        except Exception as e:
            print(f"Error en analyze_similarities: {e}")
            return []