"""
Dialog Handler - User interaction interface.

This module handles text input from the user and coordinates
between the executive agent and the cortex.
"""

import asyncio
from typing import Optional
from executive import Executive
from cortex import RoverCortex


class DialogHandler:
    """
    Handles user input and coordinates system responses.
    """
    
    def __init__(self, executive: Executive, cortex: RoverCortex):
        """
        Initialize the dialog handler.
        
        Args:
            executive: The executive agent instance
            cortex: The cortex controller instance
        """
        self.executive = executive
        self.cortex = cortex
        self.running = False
    
    def _display_user_input(self, text: str):
        """Display user input with formatting."""
        print(f"\n👤 You: {text}")
    
    def _display_agent_response(self, text: str):
        """Display agent response with formatting."""
        print(f"🤖 Marvin: {text}")
    
    def _display_system_message(self, text: str):
        """Display system message with formatting."""
        print(f"\n⚠️  System: {text}\n")
    
    def _display_status(self):
        """Display current status of the system."""
        print("\n" + "="*60)
        print(f"{self.executive.high_level_state.get_summary()}")
        print(f"Rover: {self.cortex.state.get_summary()}")
        print("="*60 + "\n")
    
    async def process_user_input(self, user_input: str):
        """
        Process user input and generate appropriate response.
        
        Args:
            user_input: The text entered by the user
        """
        self._display_user_input(user_input)
        
        # Handle special commands
        if user_input.lower().strip() == "stop":
            self.cortex.emergency_stop()
            self._display_system_message("Emergency stop activated!")
            return
        
        if user_input.lower().strip() == "status":
            self._display_status()
            return
        
        if user_input.lower().strip() in ["quit", "exit"]:
            self._display_system_message("Shutting down...")
            self.running = False
            return
        
        # Process through executive agent
        try:
            response = await self.executive.process_prompt(user_input)
            self._display_agent_response(response)
        except Exception as e:
            self._display_system_message(f"Error: {str(e)}")
    
    async def run_interactive(self):
        """
        Run the interactive dialog loop.
        Reads from terminal and processes commands.
        """
        self.running = True
        
        print("\n" + "="*60)
        print("🤖 Marvin Executive System")
        print("="*60)
        print("Commands:")
        print("  - Type your instructions or questions")
        print("  - 'stop' - Emergency stop the rover")
        print("  - 'status' - Show current status")
        print("  - 'quit' or 'exit' - Shutdown system")
        print("="*60 + "\n")
        
        # Run dialog loop in parallel with cortex
        try:
            while self.running:
                try:
                    # Use asyncio to get input without blocking
                    user_input = await asyncio.get_event_loop().run_in_executor(
                        None, 
                        input,
                        "Enter command: "
                    )
                    
                    if user_input.strip():
                        await self.process_user_input(user_input)
                    
                except EOFError:
                    break
                except KeyboardInterrupt:
                    print("\n")
                    self._display_system_message("Interrupted by user")
                    break
                    
        finally:
            self.cortex.stop_loop()
            print("\nDialog handler stopped.")
