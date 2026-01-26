#!/usr/bin/env python3
"""
Main entry point for the Marvin Executive System.

This script initializes all components and starts the rover control system.
"""

import asyncio
from executive import Executive
from cortex import RoverCortex
from dialog import DialogHandler


async def main():
    """Main function to run the system."""
    
    print("Initializing Marvin Executive System...")
    cortex = RoverCortex()
    executive = Executive(cortex)
    dialog = DialogHandler(executive, cortex)
    executive.set_output(dialog)
    
    # Start the cortex control loop and dialog handler concurrently
    try:
        await asyncio.gather(
            cortex.run(),
            executive.run(),
            dialog.run_interactive()
        )
    except KeyboardInterrupt:
        print("\n\nShutdown requested...")
    finally:
        executive.quit()
        print("System stopped.")


if __name__ == "__main__":
    asyncio.run(main())
