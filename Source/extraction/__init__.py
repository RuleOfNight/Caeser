from typing import Iterable, List, Tuple

from parsing.parser import parse_file_with_source

from .extractor import extract
from .models import GraphEdge, GraphNode


def extract_from_file(file_path: str) -> Tuple[List[GraphNode], List[GraphEdge]]:
	tree, source = parse_file_with_source(file_path)
	return extract(tree, file_path, source)


def extract_from_files(file_paths: Iterable[str]) -> Tuple[List[GraphNode], List[GraphEdge]]:
	all_nodes: List[GraphNode] = []
	all_edges: List[GraphEdge] = []
	for file_path in file_paths:
		nodes, edges = extract_from_file(file_path)
		all_nodes.extend(nodes)
		all_edges.extend(edges)
	return all_nodes, all_edges
