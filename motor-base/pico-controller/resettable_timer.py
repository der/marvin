from machine import Timer

class ResettableTimer:
    def __init__(self, timeout_ms, callback):
        """
        Initialize a resettable timer.
        
        Args:
            timeout_ms: Timeout in milliseconds
            callback: Function to call when timeout occurs
        """
        self.timeout_ms = timeout_ms
        self.callback = callback
        self.timer = Timer()
        self.is_running = False
    
    def start(self):
        """Start or restart the timer"""
        if self.is_running:
            self.timer.deinit()
        
        self.timer.init(period=self.timeout_ms, mode=Timer.ONE_SHOT, 
                        callback=lambda t: self._timeout_handler())
        self.is_running = True
    
    def _timeout_handler(self):
        self.is_running = False
        self.callback()
    
    def reset(self):
        """Reset the timer"""
        self.start()
    
    def stop(self):
        """Stop the timer"""
        if self.is_running:
            self.timer.deinit()
            self.is_running = False
