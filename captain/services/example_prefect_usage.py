#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Example usage of the Prefect-based Change Executor

This demonstrates how to use the PrefectChangeExecutor to manage
real-time code changes while workflows are running.
"""

import asyncio
import time

from captain.services.change_queue import (
    BlockChange,
    ChangeQueueManager,
    ChangeTransaction,
    ChangeType,
)


async def main():
    """Demonstrate Prefect-based change execution."""

    # Get the change queue manager
    change_queue = ChangeQueueManager.get_instance()

    # Enable Prefect execution
    print("Enabling Prefect execution...")
    if change_queue.enable_prefect_execution():
        print("✓ Prefect execution enabled")
    else:
        print("✗ Failed to enable Prefect execution")
        return

    # Create a sample block change
    block_change = BlockChange(
        block_path="/path/to/blocks/MATH/ADDITION/ADDITION.py",
        block_id="ADDITION_1",
        change_type=ChangeType.CODE_UPDATE,
        old_value="""
def add(a, b):
    \"\"\"Add two numbers.\"\"\"
    return a + b
""",
        new_value="""
def add(a, b):
    \"\"\"Add two numbers with logging.\"\"\"
    print(f"Adding {a} + {b}")
    result = a + b
    print(f"Result: {result}")
    return result
""",
    )

    # Create a transaction with the change
    transaction = ChangeTransaction(changes=[block_change])

    print(f"\nSubmitting transaction {transaction.id} to Prefect...")

    # Submit to Prefect for execution
    flow_run_id = await change_queue.submit_to_prefect(transaction)
    print(f"✓ Submitted to Prefect (flow_run_id: {flow_run_id})")

    # Check status
    print("\nChecking flow status...")
    status = change_queue.get_prefect_flow_status(transaction.id)
    if status:
        print(f"Status: {status}")

    # Simulate some work while changes are being applied
    print("\nSimulating workflow execution...")
    for i in range(5):
        print(f"  Working... {i + 1}/5")
        time.sleep(1)

        # Check if block has pending changes
        if change_queue.has_pending_changes("ADDITION_1"):
            print("  ⚠️  Block has pending changes")

    print("\nExample completed!")

    # Disable Prefect execution
    change_queue.disable_prefect_execution()
    print("✓ Prefect execution disabled")


if __name__ == "__main__":
    asyncio.run(main())
