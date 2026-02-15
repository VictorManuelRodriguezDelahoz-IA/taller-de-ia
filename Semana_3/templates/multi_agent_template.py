"""
Multi-Agent Template
====================

Plantilla para crear sistemas multi-agente con LangGraph.
"""

from typing import TypedDict, Annotated, List
from langgraph.graph import StateGraph, END
from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate
from langchain.schema import StrOutputParser
import operator


# Definir el estado compartido
class AgentState(TypedDict):
    """Estado compartido entre agentes."""
    task: str
    results: Annotated[List[str], operator.add]
    final_output: str


class MultiAgentSystem:
    """Sistema multi-agente con roles especializados."""
    
    def __init__(self, model: str = "gpt-4"):
        self.llm = ChatOpenAI(model=model, temperature=0.7)
        self.graph = self._create_graph()
    
    def _create_graph(self):
        """Crea el grafo de agentes."""
        workflow = StateGraph(AgentState)
        
        # Agregar nodos (agentes)
        workflow.add_node("researcher", self.researcher_agent)
        workflow.add_node("analyst", self.analyst_agent)
        workflow.add_node("writer", self.writer_agent)
        
        # Definir flujo
        workflow.set_entry_point("researcher")
        workflow.add_edge("researcher", "analyst")
        workflow.add_edge("analyst", "writer")
        workflow.add_edge("writer", END)
        
        return workflow.compile()
    
    def researcher_agent(self, state: AgentState) -> AgentState:
        """Agente que investiga el tema."""
        prompt = ChatPromptTemplate.from_template(
            "Investiga sobre: {task}. Proporciona 3 puntos clave."
        )
        chain = prompt | self.llm | StrOutputParser()
        result = chain.invoke({"task": state["task"]})
        
        state["results"].append(f"Investigación: {result}")
        return state
    
    def analyst_agent(self, state: AgentState) -> AgentState:
        """Agente que analiza la información."""
        prompt = ChatPromptTemplate.from_template(
            "Analiza esta información y extrae insights:\\n{info}"
        )
        chain = prompt | self.llm | StrOutputParser()
        result = chain.invoke({"info": state["results"][-1]})
        
        state["results"].append(f"Análisis: {result}")
        return state
    
    def writer_agent(self, state: AgentState) -> AgentState:
        """Agente que escribe el reporte final."""
        prompt = ChatPromptTemplate.from_template(
            "Escribe un reporte conciso basado en:\\n{info}"
        )
        chain = prompt | self.llm | StrOutputParser()
        result = chain.invoke({"info": "\\n".join(state["results"])})
        
        state["final_output"] = result
        return state
    
    def run(self, task: str) -> str:
        """Ejecuta el sistema multi-agente."""
        initial_state = {
            "task": task,
            "results": [],
            "final_output": ""
        }
        
        final_state = self.graph.invoke(initial_state)
        return final_state["final_output"]


# Ejemplo de uso
if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    
    system = MultiAgentSystem()
    result = system.run("Inteligencia Artificial en la educación")
    
    print("🤖 Sistema Multi-Agente")
    print("="*80)
    print(result)
