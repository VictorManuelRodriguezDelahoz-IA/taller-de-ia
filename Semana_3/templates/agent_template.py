"""
Agent Template
==============

Plantilla reutilizable para crear agentes con LangChain.
Personaliza este template para tus propios agentes.

"""

from langchain.agents import AgentExecutor, create_openai_functions_agent
from langchain_openai import ChatOpenAI
from langchain.tools import Tool
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
from typing import List, Callable
import os


class AgentTemplate:
    """
    Plantilla base para crear agentes personalizados.
    
    Uso:
        agent = AgentTemplate(
            name="Mi Agente",
            description="Descripción del agente",
            tools=[tool1, tool2]
        )
        result = agent.run("Haz algo")
    """
    
    def __init__(
        self,
        name: str,
        description: str,
        tools: List[Tool],
        model: str = "gpt-4",
        temperature: float = 0.7,
        max_iterations: int = 10,
        verbose: bool = True
    ):
        """
        Inicializa el agente.
        
        Args:
            name: Nombre del agente
            description: Descripción de qué hace el agente
            tools: Lista de herramientas disponibles
            model: Modelo de LLM a usar
            temperature: Temperatura del modelo
            max_iterations: Máximo de iteraciones del agente
            verbose: Si mostrar logs detallados
        """
        self.name = name
        self.description = description
        self.tools = tools
        self.verbose = verbose
        
        # Inicializar LLM
        self.llm = ChatOpenAI(
            model=model,
            temperature=temperature,
            api_key=os.getenv("OPENAI_API_KEY")
        )
        
        # Crear prompt del sistema
        self.system_prompt = self._create_system_prompt()
        
        # Crear agente
        self.agent = self._create_agent()
        
        # Crear executor
        self.executor = AgentExecutor(
            agent=self.agent,
            tools=self.tools,
            max_iterations=max_iterations,
            verbose=verbose,
            handle_parsing_errors=True
        )
    
    def _create_system_prompt(self) -> ChatPromptTemplate:
        """Crea el prompt del sistema para el agente."""
        
        system_message = f"""Eres {self.name}.

{self.description}

Tienes acceso a las siguientes herramientas:
{{tools}}

Usa las herramientas cuando sea necesario para responder las preguntas del usuario.
Piensa paso a paso y explica tu razonamiento.

Si no puedes responder con certeza, di que no lo sabes.
Sé conciso pero completo en tus respuestas.
"""
        
        prompt = ChatPromptTemplate.from_messages([
            ("system", system_message),
            MessagesPlaceholder(variable_name="chat_history", optional=True),
            ("human", "{input}"),
            MessagesPlaceholder(variable_name="agent_scratchpad")
        ])
        
        return prompt
    
    def _create_agent(self):
        """Crea el agente con el prompt y herramientas."""
        return create_openai_functions_agent(
            llm=self.llm,
            tools=self.tools,
            prompt=self.system_prompt
        )
    
    def run(self, query: str, chat_history: List = None) -> str:
        """
        Ejecuta el agente con una consulta.
        
        Args:
            query: Consulta del usuario
            chat_history: Historial de chat (opcional)
            
        Returns:
            Respuesta del agente
        """
        result = self.executor.invoke({
            "input": query,
            "chat_history": chat_history or []
        })
        
        return result["output"]
    
    def add_tool(self, tool: Tool):
        """Agrega una herramienta al agente."""
        self.tools.append(tool)
        # Recrear agente con nueva herramienta
        self.agent = self._create_agent()
        self.executor.agent = self.agent


# Funciones helper para crear tools
def create_tool(
    name: str,
    description: str,
    func: Callable
) -> Tool:
    """
    Crea una herramienta para el agente.
    
    Args:
        name: Nombre de la herramienta
        description: Descripción de qué hace (importante para que el agente sepa cuándo usarla)
        func: Función a ejecutar
        
    Returns:
        Tool configurada
    """
    return Tool(
        name=name,
        description=description,
        func=func
    )


# Ejemplo de uso
if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    
    # Definir herramientas de ejemplo
    def calculadora(expresion: str) -> str:
        """Evalúa una expresión matemática."""
        try:
            result = eval(expresion)
            return f"El resultado es: {result}"
        except Exception as e:
            return f"Error al calcular: {e}"
    
    def obtener_fecha() -> str:
        """Obtiene la fecha actual."""
        from datetime import datetime
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # Crear tools
    tools = [
        create_tool(
            name="calculadora",
            description="Útil para realizar cálculos matemáticos. Input debe ser una expresión matemática válida.",
            func=calculadora
        ),
        create_tool(
            name="obtener_fecha",
            description="Obtiene la fecha y hora actual.",
            func=obtener_fecha
        )
    ]
    
    # Crear agente
    agent = AgentTemplate(
        name="Asistente Matemático",
        description="Un asistente que puede realizar cálculos y proporcionar la fecha actual.",
        tools=tools,
        verbose=True
    )
    
    # Probar agente
    print("🤖 Agente creado. Probando...")
    print("\n" + "="*80 + "\n")
    
    queries = [
        "¿Cuánto es 25 * 4 + 10?",
        "¿Qué fecha es hoy?",
        "Calcula el área de un círculo con radio 5 (usa pi=3.14159)"
    ]
    
    for query in queries:
        print(f"👤 Usuario: {query}")
        response = agent.run(query)
        print(f"🤖 Agente: {response}")
        print("\n" + "-"*80 + "\n")
