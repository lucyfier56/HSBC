from services.vector_db import search_knowledge_base

def retrieve(query: str, top_k: int = 3):
    """Retrieve relevant information from the knowledge base"""
    try:
        results = search_knowledge_base(query, top_k)
        
        if results:
            return {
                "status": "success",
                "results": results,
                "summary": "\n\n".join([r["content"] for r in results])
            }
        else:
            return {
                "status": "no_results",
                "message": "No relevant information found in the knowledge base."
            }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Error searching knowledge base: {str(e)}"
        }
