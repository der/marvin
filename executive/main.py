#!/usr/bin/env python3
"""
Main entry point for the Marvin Executive System.

This script initializes all components and starts the rover control system.
"""

import asyncio
import argparse
from executive import ExecutiveAgent
from cortex import RoverCortex
from dialog import DialogHandler


async def main():
    """Main function to run the system."""
    
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Marvin Executive System')
    parser.add_argument(
        '--model-url',
        default='http://localhost:8080/v1',
        help='Base URL for the LLM API (default: http://localhost:8080/v1)'
    )
    parser.add_argument(
        '--model-name',
        default='local-model',
        help='Model name/identifier (default: local-model)'
    )
    parser.add_argument(
        '--update-interval',
        type=float,
        default=0.2,
        help='Cortex state update interval in seconds (default: 0.2)'
    )
    
    args = parser.parse_args()
    
    print("Initializing Marvin Executive System...")
    print(f"LLM Model: {args.model_name} @ {args.model_url}")
    print(f"Update interval: {args.update_interval}s")
    
    # Initialize components
    cortex = RoverCortex(update_interval=args.update_interval)
    executive = ExecutiveAgent(
        model_url=args.model_url,
        model_name=args.model_name
    )
    dialog = DialogHandler(executive, cortex)
    
    print("All components initialized.\n")
    
    # Start the cortex control loop and dialog handler concurrently
    try:
        await asyncio.gather(
            cortex.run(),
            dialog.run_interactive()
        )
    except KeyboardInterrupt:
        print("\n\nShutdown requested...")
    finally:
        cortex.stop_loop()
        print("System stopped.")


if __name__ == "__main__":
    asyncio.run(main())
