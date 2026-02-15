"""
Script de Migración de Datos para RAG
======================================

Este script migra documentos a una base de datos vectorial (ChromaDB)
para su uso en sistemas RAG.

Uso:
    python db_migration.py --input_dir ./data --collection_name documentos

"""

import os
import argparse
from pathlib import Path
from typing import List, Dict
import chromadb
from chromadb.config import Settings
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.embeddings import HuggingFaceEmbeddings
from tqdm import tqdm


class DocumentMigrator:
    """Migra documentos a ChromaDB."""
    
    def __init__(self, persist_directory: str = "./chroma_db"):
        """
        Inicializa el migrador.
        
        Args:
            persist_directory: Directorio donde se guardará la base de datos
        """
        self.persist_directory = persist_directory
        
        # Inicializar ChromaDB
        self.client = chromadb.Client(Settings(
            persist_directory=persist_directory,
            anonymized_telemetry=False
        ))
        
        # Inicializar modelo de embeddings
        print("🔄 Cargando modelo de embeddings...")
        self.embeddings = HuggingFaceEmbeddings(
            model_name="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
        )
        print("✅ Modelo cargado")
        
        # Configurar text splitter
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=500,
            chunk_overlap=50,
            length_function=len,
            separators=["\n\n", "\n", ". ", " ", ""]
        )
    
    def read_documents(self, input_dir: str) -> List[Dict[str, str]]:
        """
        Lee todos los documentos de texto del directorio.
        
        Args:
            input_dir: Directorio con los documentos
            
        Returns:
            Lista de diccionarios con contenido y metadata
        """
        documents = []
        input_path = Path(input_dir)
        
        # Extensiones soportadas
        extensions = ['.txt', '.md']
        
        print(f"📂 Leyendo documentos de {input_dir}...")
        
        for ext in extensions:
            for file_path in input_path.glob(f"**/*{ext}"):
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                        
                    documents.append({
                        'content': content,
                        'metadata': {
                            'source': str(file_path),
                            'filename': file_path.name,
                            'extension': ext
                        }
                    })
                    print(f"  ✅ {file_path.name}")
                    
                except Exception as e:
                    print(f"  ❌ Error leyendo {file_path.name}: {e}")
        
        print(f"\\n📊 Total documentos leídos: {len(documents)}")
        return documents
    
    def chunk_documents(self, documents: List[Dict[str, str]]) -> List[Dict[str, any]]:
        """
        Divide documentos en chunks.
        
        Args:
            documents: Lista de documentos
            
        Returns:
            Lista de chunks con metadata
        """
        print("\\n✂️ Dividiendo documentos en chunks...")
        
        all_chunks = []
        
        for doc in tqdm(documents, desc="Procesando"):
            chunks = self.text_splitter.split_text(doc['content'])
            
            for i, chunk in enumerate(chunks):
                chunk_data = {
                    'content': chunk,
                    'metadata': {
                        **doc['metadata'],
                        'chunk_id': i,
                        'total_chunks': len(chunks)
                    }
                }
                all_chunks.append(chunk_data)
        
        print(f"✅ Total chunks creados: {len(all_chunks)}")
        return all_chunks
    
    def migrate_to_chromadb(self, chunks: List[Dict[str, any]], collection_name: str):
        """
        Migra chunks a ChromaDB.
        
        Args:
            chunks: Lista de chunks
            collection_name: Nombre de la colección
        """
        print(f"\\n💾 Migrando a ChromaDB (colección: {collection_name})...")
        
        # Crear o obtener colección
        try:
            self.client.delete_collection(collection_name)
            print(f"  🗑️ Colección existente eliminada")
        except:
            pass
        
        collection = self.client.create_collection(
            name=collection_name,
            metadata={"description": "Documentos para RAG"}
        )
        
        # Preparar datos para inserción
        texts = [chunk['content'] for chunk in chunks]
        metadatas = [chunk['metadata'] for chunk in chunks]
        ids = [f"doc_{i}" for i in range(len(chunks))]
        
        # Generar embeddings y agregar a la colección
        print("  🔄 Generando embeddings...")
        embeddings_list = self.embeddings.embed_documents(texts)
        
        # Insertar en batches
        batch_size = 100
        for i in tqdm(range(0, len(texts), batch_size), desc="Insertando"):
            end_idx = min(i + batch_size, len(texts))
            
            collection.add(
                embeddings=embeddings_list[i:end_idx],
                documents=texts[i:end_idx],
                metadatas=metadatas[i:end_idx],
                ids=ids[i:end_idx]
            )
        
        print(f"✅ Migración completada: {len(chunks)} chunks insertados")
        
        # Estadísticas
        print(f"\\n📊 Estadísticas de la colección:")
        print(f"  - Nombre: {collection_name}")
        print(f"  - Total documentos: {collection.count()}")
        print(f"  - Directorio: {self.persist_directory}")
    
    def test_search(self, collection_name: str, query: str, n_results: int = 3):
        """
        Prueba la búsqueda en la colección.
        
        Args:
            collection_name: Nombre de la colección
            query: Consulta de búsqueda
            n_results: Número de resultados
        """
        print(f"\\n🔍 Probando búsqueda: '{query}'")
        
        collection = self.client.get_collection(collection_name)
        query_embedding = self.embeddings.embed_query(query)
        
        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=n_results
        )
        
        print(f"\\n📋 Top {n_results} resultados:\\n")
        for i, (doc, metadata, distance) in enumerate(zip(
            results['documents'][0],
            results['metadatas'][0],
            results['distances'][0]
        ), 1):
            print(f"{i}. Fuente: {metadata.get('filename', 'N/A')}")
            print(f"   Similitud: {1 - distance:.4f}")
            print(f"   Contenido: {doc[:200]}...")
            print()


def main():
    parser = argparse.ArgumentParser(description="Migrar documentos a ChromaDB")
    parser.add_argument(
        "--input_dir",
        type=str,
        default="./data",
        help="Directorio con documentos de entrada"
    )
    parser.add_argument(
        "--collection_name",
        type=str,
        default="documentos",
        help="Nombre de la colección en ChromaDB"
    )
    parser.add_argument(
        "--persist_dir",
        type=str,
        default="./chroma_db",
        help="Directorio para persistir ChromaDB"
    )
    parser.add_argument(
        "--test_query",
        type=str,
        default=None,
        help="Consulta de prueba después de la migración"
    )
    
    args = parser.parse_args()
    
    # Crear migrador
    migrator = DocumentMigrator(persist_directory=args.persist_dir)
    
    # Leer documentos
    documents = migrator.read_documents(args.input_dir)
    
    if not documents:
        print("❌ No se encontraron documentos para migrar")
        return
    
    # Crear chunks
    chunks = migrator.chunk_documents(documents)
    
    # Migrar a ChromaDB
    migrator.migrate_to_chromadb(chunks, args.collection_name)
    
    # Prueba opcional
    if args.test_query:
        migrator.test_search(args.collection_name, args.test_query)
    
    print("\\n✅ ¡Proceso completado exitosamente!")


if __name__ == "__main__":
    main()
