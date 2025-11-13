"""
Visualize the LangGraph agent structure.

This script generates a visual representation of the agent's graph.
Requires: pip install pygraphviz (optional)
"""

from agent import create_graph


def visualize_graph():
    """Generate and display the graph visualization."""
    graph = create_graph()

    try:
        # Try to create a mermaid diagram
        print("Graph Structure (Mermaid Diagram):")
        print("=" * 60)
        print(graph.get_graph().draw_mermaid())
        print("=" * 60)
        print()
        print("Copy the above diagram to https://mermaid.live for visualization")
    except Exception as e:
        print(f"Error generating visualization: {e}")
        print("Install mermaid support or use LangGraph Studio for visualization")

    # Print text representation
    print("\nGraph Nodes:")
    print("=" * 60)
    nodes = ["safety_check", "reject", "agent"]
    for node in nodes:
        print(f"  - {node}")

    print("\nGraph Edges:")
    print("=" * 60)
    print("  - START → safety_check")
    print("  - safety_check → reject (if unsafe)")
    print("  - safety_check → agent (if safe)")
    print("  - reject → END")
    print("  - agent → END")
    print("=" * 60)


if __name__ == "__main__":
    visualize_graph()

