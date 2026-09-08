from langgraph.graph import StateGraph, END
from backend.agents.state import TranslationState
from backend.agents.extractor_agent import extractor_node
from backend.agents.translator_agent import translator_node
from backend.agents.reviewer_agent import reviewer_node

def should_continue(state: TranslationState) -> str:
    """
    Función de decisión para la transición condicional de LangGraph.
    Si hay error o si la revisión está aprobada, finaliza (END).
    Si no, vuelve a invocar al nodo 'translator'.
    """
    if state.get("error"):
        return END
    if state.get("revision_aprobada", False):
        return END
    if state.get("intento_revision", 0) >= 2:
        return END
    return "translator"

# Construcción del grafo de estado
workflow = StateGraph(TranslationState)

# Adición de nodos
workflow.add_node("extractor", extractor_node)
workflow.add_node("translator", translator_node)
workflow.add_node("reviewer", reviewer_node)

# Flujo de ejecución
workflow.set_entry_point("extractor")
workflow.add_edge("extractor", "translator")
workflow.add_edge("translator", "reviewer")

# Transición condicional basada en el estado de la revisión
workflow.add_conditional_edges(
    "reviewer",
    should_continue,
    {
        "translator": "translator",
        END: END
    }
)

# Compilación del grafo
orchestrator_pipeline = workflow.compile()
