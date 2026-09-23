"""Component swapping and improvement testing."""

from __future__ import annotations

import copy

from autoengineering.system.component import Component
from autoengineering.system.graph import System


def swap_component(
    system: System,
    target_name: str,
    replacement: Component | dict,
) -> System:
    """Create a new system with one component replaced.

    The replacement inherits all connections from the original component.

    Args:
        system: Original system.
        target_name: Name of component to replace.
        replacement: New Component or dict (passed to Component.from_dict).

    Returns:
        A new System with the component swapped.
    """
    # Validate target exists
    system.get_component(target_name)

    if isinstance(replacement, dict):
        replacement = Component.from_dict(replacement)

    # Build a new system
    new_system = System(name=system.name, description=system.description)

    # Copy all components, replacing the target
    for name in system.component_names:
        if name == target_name:
            new_system._graph.add_node(
                replacement.name, component=replacement
            )
        else:
            comp = copy.deepcopy(system.get_component(name))
            new_system._graph.add_node(name, component=comp)

    # Copy all connections, updating references if component name changed
    new_name = replacement.name
    for conn in system.connections:
        source = new_name if conn["source"] == target_name else conn["source"]
        target = new_name if conn["target"] == target_name else conn["target"]
        new_system._graph.add_edge(
            source,
            target,
            port_from=conn.get("port_from", ""),
            port_to=conn.get("port_to", ""),
            description=conn.get("description", ""),
        )

    return new_system
