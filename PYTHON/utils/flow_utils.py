#!/usr/bin/env python3
# Copyright (c) 2024 Emasoft
#
# This file is part of AtlasVibe, which is based on Flojoy Studio
# Original Copyright (c) 2023-2024 Flojoy
#
# SPDX-License-Identifier: MIT
# See the LICENSE file for details.

# -*- coding: utf-8 -*-

# HERE IS THE CHANGELOG FOR THIS VERSION OF THE CODE:
# - Added functions to save and load flow data using json_utils
# - Made debug printing configurable via DEBUG flag
# - Added error handling with logging
# - Added export functions for flow analysis
#

import json
from pathlib import Path
from typing import Optional, Dict, Any, List, Tuple
from .flows import Flows
from .graph import Graph
from captain.utils.shared.json_utils import save_json_file, load_json_file
from captain.utils.shared.error_utils import with_error_handling, error_context
from captain.utils.logger import logger

# Debug flag - set to False in production
DEBUG = False


def find_flows(graph: Graph, node_by_serial: Dict[int, Dict[str, Any]], cmds: List[str]) -> Flows:
    """
    Given a list of commands it returns a dictionary with their flows

    Args:
        graph: The graph structure containing nodes and edges
        node_by_serial: Dictionary mapping serial numbers to node data
        cmds: List of command types to track flows for

    Returns:
        Flows object containing the discovered flows
    """
    flows = Flows()

    def dfs(source: int) -> List[str]:
        childs = []
        cmd = node_by_serial[source]["cmd"]
        node_id = node_by_serial[source]["id"]

        # if node doesn't have any child, return itself as the only child in this branch
        if source not in graph.adj_list.keys():
            # ignoring as source does not have any child
            return [node_id]

        for value in graph.adj_list[source]:
            child_source = value["target_node"]
            if cmd in cmds:
                child_node_ids = dfs(source=child_source)
                # childs = childs + child_node_ids

                # record the childs for the direction
                direction = value["handle"].lower()
                flows.extend_flow(node_id, direction, child_node_ids)

                if DEBUG:
                    print(
                        "source:",
                        source,
                        "childs",
                        child_node_ids,
                        "were added for direction:",
                        direction,
                        "| all childs:",
                        flows.get_flow(node_id, direction),
                        "| node_id:",
                        node_id,
                    )
            else:
                # ignoring as its not a special command
                child_node_ids = dfs(source=child_source)
                childs = childs + child_node_ids
        return [node_id] + childs

    # finding the source of dfs tree which are nodes without any incoming edge
    dfs_sources = []
    for node in graph.DG.nodes:
        if len(list(graph.DG.predecessors(node))) == 0:
            dfs_sources.append(node)

    for source in dfs_sources:
        dfs(source=source)

    return flows


def apply_topology(flows: Flows, topology: List[int]) -> None:
    """
    Fixes the ordering of nodes in the given flows according to the provided topology

    Args:
        flows: Flows object to modify
        topology: List of serial numbers in desired order
    """
    if DEBUG:
        print(
            "apply topology, for flows:",
            json.dumps(flows.all_node_data, indent=2),
            "\nbefore state:",
            topology,
        )

    new_flows = Flows()
    for serial in topology:
        for node_id, node_data in flows.all_node_data.items():
            for direction, _ in node_data.items():
                if serial in flows.get_flow(node_id, direction):
                    new_flows.extend_flow(node_id, direction, [serial])
    flows.from_flows(new_flows)
    # print('apply topology, after state:', topology)


def gather_all_flow_nodes(flows: Flows) -> List[int]:
    """
    Gather all node serials from flows

    Args:
        flows: Flows object to gather nodes from

    Returns:
        List of all node serial numbers in flows
    """
    node_serials = []
    for node_id, node_data in flows.all_node_data.items():
        for direction, child_ids in node_data.items():
            for child_id in child_ids:
                try:
                    node_serials += [child_id]
                except Exception:
                    pass
    return node_serials


@with_error_handling(default=False, logger=logger)
def save_flows_to_file(flows: Flows, file_path: Path | str, metadata: Optional[Dict[str, Any]] = None) -> bool:
    """
    Save flows to a JSON file using atomic operations.

    Args:
        flows: Flows object to save
        file_path: Path to save the flows to
        metadata: Optional metadata to include

    Returns:
        True if successful, False otherwise
    """
    with error_context("saving flows to file", logger):
        flow_data = {
            "flows": flows.all_node_data,
            "metadata": metadata or {},
        }
        return save_json_file(file_path, flow_data)


@with_error_handling(default=None, logger=logger)
def load_flows_from_file(
    file_path: Path | str,
) -> Optional[Tuple[Flows, Dict[str, Any]]]:
    """
    Load flows from a JSON file.

    Args:
        file_path: Path to load flows from

    Returns:
        Tuple of (Flows object, metadata) if successful, None otherwise
    """
    with error_context("loading flows from file", logger):
        data = load_json_file(file_path)
        if data and "flows" in data:
            flows = Flows()
            flows.all_node_data = data["flows"]
            return flows, data.get("metadata", {})
        return None


@with_error_handling(default=False, logger=logger)
def export_flow_analysis(
    flows: Flows,
    output_path: Path | str,
    include_topology: Optional[List[int]] = None,
    include_nodes: bool = True,
) -> bool:
    """
    Export comprehensive flow analysis to JSON file.

    Args:
        flows: Flows object to analyze
        output_path: Path to save analysis
        include_topology: Optional topology to include
        include_nodes: Whether to include node analysis

    Returns:
        True if successful, False otherwise
    """
    with error_context("exporting flow analysis", logger):
        analysis = {
            "flow_count": len(flows.all_node_data),
            "flows": flows.all_node_data,
        }

        if include_nodes:
            all_nodes = gather_all_flow_nodes(flows)
            analysis["all_flow_nodes"] = all_nodes
            analysis["unique_node_count"] = len(set(all_nodes))
            analysis["total_connections"] = len(all_nodes)

        if include_topology:
            analysis["topology"] = include_topology

        return save_json_file(output_path, analysis, indent=2)


def enable_debug_mode(enabled: bool = True) -> None:
    """
    Enable or disable debug printing.

    Args:
        enabled: Whether to enable debug mode
    """
    global DEBUG
    DEBUG = enabled
    logger.info(f"Flow utils debug mode: {'enabled' if enabled else 'disabled'}")
