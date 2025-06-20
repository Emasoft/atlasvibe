#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# HERE IS THE CHANGELOG FOR THIS VERSION OF THE CODE:
# - Created tests for refactored flow_utils.py
# - Tests usage of json_utils for saving flow data
# - Following TDD methodology
#

"""
Test suite for refactored flow_utils.py with json utilities integration.
"""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch
import tempfile

from PYTHON.utils.flow_utils import find_flows, apply_topology, gather_all_flow_nodes
from PYTHON.utils.flows import Flows
from PYTHON.utils.graph import Graph
from captain.utils.shared.json_utils import save_json_file, load_json_file


class TestFlowUtilsRefactored:
    """Test flow utilities with JSON operations."""

    @pytest.fixture
    def mock_graph(self):
        """Create a mock graph for testing."""
        graph = Mock(spec=Graph)
        graph.DG = Mock()
        graph.DG.nodes = [1, 2, 3, 4]
        graph.DG.predecessors = Mock(side_effect=lambda n: [] if n == 1 else [n - 1])
        graph.adj_list = {
            1: [{"target_node": 2, "handle": "true"}],
            2: [
                {"target_node": 3, "handle": "false"},
                {"target_node": 4, "handle": "true"},
            ],
        }
        return graph

    @pytest.fixture
    def node_by_serial(self):
        """Create node mapping for testing."""
        return {
            1: {"id": "node_1", "cmd": "IF"},
            2: {"id": "node_2", "cmd": "WHILE"},
            3: {"id": "node_3", "cmd": "PRINT"},
            4: {"id": "node_4", "cmd": "RETURN"},
        }

    def test_find_flows_basic(self, mock_graph, node_by_serial):
        """Test basic flow finding functionality."""
        # Execute
        flows = find_flows(mock_graph, node_by_serial, ["IF", "WHILE"])

        # Assert
        assert isinstance(flows, Flows)
        # Check that flows were recorded for IF and WHILE commands
        assert flows.get_flow("node_1", "true") is not None
        assert flows.get_flow("node_2", "false") is not None
        assert flows.get_flow("node_2", "true") is not None

    def test_save_flows_to_json(self, mock_graph, node_by_serial):
        """Test saving flows to JSON using json_utils."""
        # Find flows
        flows = find_flows(mock_graph, node_by_serial, ["IF", "WHILE"])

        # Save to temporary file
        with tempfile.TemporaryDirectory() as tmpdir:
            flow_file = Path(tmpdir) / "flows.json"

            # Convert flows to dictionary for saving
            flow_data = {
                "flows": flows.all_node_data,
                "metadata": {
                    "version": "1.0",
                    "command_types": ["IF", "WHILE"],
                },
            }

            # Save using json_utils
            success = save_json_file(flow_file, flow_data)
            assert success is True

            # Verify file exists and can be loaded
            loaded_data = load_json_file(flow_file)
            assert loaded_data is not None
            assert "flows" in loaded_data
            assert loaded_data["metadata"]["version"] == "1.0"

    def test_apply_topology_with_save(self, mock_graph, node_by_serial):
        """Test applying topology and saving results."""
        # Setup
        flows = find_flows(mock_graph, node_by_serial, ["IF", "WHILE"])
        topology = [4, 3, 2, 1]  # Reverse order

        # Apply topology
        apply_topology(flows, topology)

        # Save topology results
        with tempfile.TemporaryDirectory() as tmpdir:
            topology_file = Path(tmpdir) / "topology.json"

            topology_data = {
                "original_topology": topology,
                "flows_after_topology": flows.all_node_data,
            }

            success = save_json_file(topology_file, topology_data)
            assert success is True

            # Verify saved data
            loaded = load_json_file(topology_file)
            assert loaded["original_topology"] == topology

    def test_gather_flow_nodes_and_export(self, mock_graph, node_by_serial):
        """Test gathering flow nodes and exporting to JSON."""
        # Setup
        flows = Flows()
        flows.extend_flow("node_1", "true", [2, 3])
        flows.extend_flow("node_1", "false", [4])
        flows.extend_flow("node_2", "true", [3])

        # Gather nodes
        node_serials = gather_all_flow_nodes(flows)

        # Export gathered nodes
        with tempfile.TemporaryDirectory() as tmpdir:
            nodes_file = Path(tmpdir) / "flow_nodes.json"

            nodes_data = {
                "all_flow_nodes": node_serials,
                "unique_nodes": list(set(node_serials)),
                "node_count": len(set(node_serials)),
            }

            success = save_json_file(nodes_file, nodes_data)
            assert success is True

            # Verify
            loaded = load_json_file(nodes_file)
            assert len(loaded["all_flow_nodes"]) == len(node_serials)
            assert loaded["node_count"] == len(set(node_serials))

    def test_flow_debugging_export(self, mock_graph, node_by_serial, capsys):
        """Test that debug output can be captured and saved."""
        # Execute with captured output
        flows = find_flows(mock_graph, node_by_serial, ["IF", "WHILE"])

        # Capture printed debug output
        captured = capsys.readouterr()

        # Save debug output to JSON
        with tempfile.TemporaryDirectory() as tmpdir:
            debug_file = Path(tmpdir) / "debug_output.json"

            debug_data = {
                "debug_output": captured.out.split("\n"),
                "flows": flows.all_node_data,
            }

            success = save_json_file(debug_file, debug_data)
            assert success is True

    def test_error_handling_with_invalid_graph(self, node_by_serial):
        """Test error handling when graph is invalid."""
        # Create invalid graph
        invalid_graph = Mock(spec=Graph)
        invalid_graph.DG = None
        invalid_graph.adj_list = {}

        # Should handle gracefully
        with pytest.raises(AttributeError):
            find_flows(invalid_graph, node_by_serial, ["IF"])

    def test_empty_flows_export(self):
        """Test exporting empty flows."""
        flows = Flows()

        with tempfile.TemporaryDirectory() as tmpdir:
            empty_file = Path(tmpdir) / "empty_flows.json"

            flow_data = {
                "flows": flows.all_node_data,
                "is_empty": len(flows.all_node_data) == 0,
            }

            success = save_json_file(empty_file, flow_data)
            assert success is True

            loaded = load_json_file(empty_file)
            assert loaded["is_empty"] is True

    @patch("PYTHON.utils.flow_utils.print")
    def test_debug_output_disabled(self, mock_print, mock_graph, node_by_serial):
        """Test that debug print statements can be controlled."""
        from PYTHON.utils.flow_utils import enable_debug_mode

        # First test with debug disabled (default)
        find_flows(mock_graph, node_by_serial, ["IF", "WHILE"])
        # Print should not be called when DEBUG is False
        assert mock_print.call_count == 0

        # Reset mock
        mock_print.reset_mock()

        # Enable debug mode
        enable_debug_mode(True)

        # Execute again
        find_flows(mock_graph, node_by_serial, ["IF", "WHILE"])

        # Now print should be called
        assert mock_print.call_count > 0

        # Restore debug mode to default
        enable_debug_mode(False)


# Run tests with: uv run pytest PYTHON/tests/test_flow_utils_refactored.py -v
