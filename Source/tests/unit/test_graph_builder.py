from graph.builder import build_node_detail_graph, build_project_graph, build_runtime_flow_graph, detect_entrypoint_nodes


def test_detect_entrypoint_and_runtime_flow(tmp_path):
    main_file = tmp_path / "main.py"
    helper_file = tmp_path / "helper.py"

    helper_file.write_text(
        """
def helper():
    return 1
""".strip(),
        encoding="utf-8",
    )

    main_file.write_text(
        """
from helper import helper


def main():
    helper()


if __name__ == "__main__":
    main()
""".strip(),
        encoding="utf-8",
    )

    graph = build_project_graph(str(tmp_path))
    roots = detect_entrypoint_nodes(graph)

    assert roots
    assert graph.nodes[roots[0]]["file_path"].endswith("main.py")

    flow_graph = build_runtime_flow_graph(graph, root_node_id=roots[0], max_depth=4)
    assert any(data.get("name") == "main" for _, data in flow_graph.nodes(data=True))
    assert any(data.get("name") == "helper" for _, data in flow_graph.nodes(data=True))
    assert any(edge_data.get("relationship") == "CALLS" for _, _, edge_data in flow_graph.edges(data=True))


def test_detail_graph_centers_on_clicked_function(tmp_path):
    main_file = tmp_path / "main.py"

    main_file.write_text(
        """
def helper_one():
    return 1


def helper_two():
    return 2


def target():
    helper_one()
""".strip(),
        encoding="utf-8",
    )

    graph = build_project_graph(str(tmp_path))
    focus_id = next(node_id for node_id, data in graph.nodes(data=True) if data.get("name") == "target")

    detail_graph = build_node_detail_graph(graph, focus_id, depth=1)

    assert any(data.get("name") == "target" for _, data in detail_graph.nodes(data=True))
    assert any(data.get("name") == "helper_one" for _, data in detail_graph.nodes(data=True))
    assert not any(data.get("name") == "helper_two" for _, data in detail_graph.nodes(data=True))