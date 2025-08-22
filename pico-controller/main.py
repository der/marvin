# Initialise hardware and framebuf before importing modules.
from color_setup import ssd,sd,touch  # Create a display instance
from gui.core.nanogui import refresh
refresh(ssd, True)  # Initialise and clear display.

# Now import other modules
from gui.widgets.label import Label
from gui.widgets.textbox import Textbox
from gui.core.writer import CWriter
import utime
import asyncio
import deflate
import network
from urllib.urequest import urlopen
from joystick_controller import JoystickController
from machine import ADC, Pin

# Configuration
ROVER="http://marvin.local:8080/"
NETWORK="amberdown"
PASSWORD="candleandthestar"

# Font for CWriter
import gui.fonts.freesans20 as font
from gui.core.colors import *

class Button:
    """A class representing a button on the display."""
    BUTTON_HEIGHT = 20
    BUTTON_WIDTH = 80

    def __init__(self, wri, text, row, col, selected=False):
        self.row = row
        self.col = col
        self.text = text
        self.selected = selected
        self.label = Label(wri, row, col, text, bdcolor=GREEN if selected else RED)

    def check_touch(self, touch):
        """Checks if the button is touched."""
        row, col = touch
        if (col > self.col and col < self.col + self.BUTTON_WIDTH and 
                row > self.row and row < self.row + self.BUTTON_HEIGHT):
            return True
        return False
    
    def set_selected(self, selected):
        """Sets the button as selected or not."""
        self.selected = selected
        self.label.value(bdcolor=GREEN if selected else RED)

class ButtonSet:
    BUTTON_LEFT = 230
    BUTTON_SPACING = 35

    """A class representing a set of buttons on the display."""
    def __init__(self, wri, labels):
        self.wri = wri
        self.offset = self.BUTTON_SPACING
        self.buttons = []
        for label in labels:
            self.add_button(label)
        self.selected_button = None
    
    def select_button(self, label):
        """Selects a button by its label."""
        for button in self.buttons:
            if button.text == label:
                button.set_selected(True)
                self.selected_button = button
            else:
                button.set_selected(False)

    def add_button(self, label):
        """Adds a button to the set."""
        self.buttons.append(Button(self.wri, label, self.offset, self.BUTTON_LEFT))
        self.offset += self.BUTTON_SPACING

    def check_touch(self, touch):
        """Checks if any button in the set is touched."""
        for button in self.buttons:
            if button.check_touch(touch) and button.text != self.selected_button.text:
                # print(f"Button {button.text} touched")
                self.selected_button.set_selected(False)
                button.set_selected(True)
                self.selected_button = button
                return button.text
        return None

class Screen:
    """A class representing a screen on the display."""
    def __init__(self, wri, name):
        self.wri = wri
        self.name = name

    async def install(self):
        """Installs the screen with any common widgets"""
        pass
    
    async def await_data(self):
        """Awaits for incoming data, that will be displayed."""
        pass

    async def update_display(self):
        """Updates the display with new data."""
        pass

    async def handle_touch(self, touch):
        """Handles touch events."""
        pass

class ImageScreen(Screen):
    """A class representing an image screen."""
    def __init__(self, wri, name, file):
        super().__init__(wri, name)
        self.file = file

    async def await_data(self):
        await asyncio.sleep(0.05)  # Simulate waiting for data

    async def update_display(self):
        """Updates the display with the image."""
        # print(f"Updating display with image {self.file}")
        with open(self.file, "rb") as f:
            f.readinto(ssd.mvb)
        refresh(ssd)  # Display the image

class WebImageScreen(Screen):
    def __init__(self, wri, name, url):
        super().__init__(wri, name)
        self.url = url

    async def await_data(self):
        # Dummy, sleep briefly just to allow touch check
        await asyncio.sleep(0.01)

    async def update_display(self):
        """Updates the display with the image."""
        try:
            # print("Trying to open", self.url)
            s = urlopen(self.url)
            with deflate.DeflateIO(s, deflate.ZLIB) as d:
                d.readinto(ssd.mvb)
            s.close()
            refresh(ssd)  # Display the image
        except Exception as e:
            print("problem fetching image", e)
            Label(self.wri, 180, 10, "Problem fetching image", bgcolor=RED)
            
    async def install(self):
        print("Camera activated")
    
class DummyScreen(Screen):
    """A class representing a dummy screen."""
    def __init__(self, wri, text):
        super().__init__(wri, text)
        self.text = text

    async def await_data(self):
        await asyncio.sleep(0.1)
        
    async def update_display(self):
        await asyncio.sleep(0.1)

    async def install(self):
        Label(self.wri, 100, 100, self.text, bgcolor=BLUE)

battery_conversion_factor = 3 * 3.3 / 65535
full_battery = 4.2
empty_battery = 2.8  

class BatteryScreen(Screen):
    """Test screen for measuring battery level"""
    def __init__(self, wri, name):
        super().__init__(wri, name)
        self.vsys = ADC(Pin(29))
        self.text = "No reading"
    
    def measure_battery(self):
        voltage = self.vsys.read_u16() * battery_conversion_factor
        print("Voltage", voltage)
        percentage = 100 * ((voltage - empty_battery) / (full_battery - empty_battery))
        if percentage > 100:
            percentage = 100.00
        return percentage, voltage
    
    async def await_data(self):
        await asyncio.sleep(0.1)
        
    async def update_display(self):
        percentage, voltage = self.measure_battery()
        self.text = f"{voltage:.2f}V {percentage:.2f}%"
        Label(self.wri, 100, 100, self.text, bgcolor=BLUE)

    async def install(self):
        Label(self.wri, 100, 100, self.text, bgcolor=BLUE)

class MessageScreen(Screen):
    """Screen to show scrolling text, remembers last message"""
    def __init__(self, wri, name):
        super().__init__(wri, name)
        self.text = name
        self.append_text = None
        
    async def install(self):
        self.textbox = Textbox(self.wri, 10, 10, 200, 10, bdcolor=BLUE)
        self.textbox.append(self.text)
        
    async def message(self, text):
        print(text)
        self.append_text = text
        
    async def await_data(self):
        if not self.append_text:
            await asyncio.sleep(0.01)
        
    async def update_display(self):
        if self.append_text:
            self.textbox.append(self.append_text)
            self.text = self.append_text
            self.append_text = None

class DisplayController:
    def __init__(self):
        """Initializes the ButtonController with a default selected button."""
        CWriter.set_textpos(ssd, 0, 0)  # In case previous tests have altered it
        self.wri = CWriter(ssd, font, WHITE, BLACK, verbose=False)
        self.wri.set_clip(True, True, False)
        self.screens = {
            "console": MessageScreen(self.wri, "console"),
#            "camera": ImageScreen(self.wri, "camera", "/sd/cat-small.bin"),
#            "camera": WebImageScreen(self.wri, "camera", "http://pi2.local:8080/still-565"),
            "camera": WebImageScreen(self.wri, "camera", ROVER + "still-565"),
#            "lidar": DummyScreen(self.wri, "lidar"),
            "battery": BatteryScreen(self.wri, "battery"),
            "range": DummyScreen(self.wri, "range"),
        }
        self.screen = self.screens["console"]
        self.init_buttons()

    def init_buttons(self):
        """Initializes the buttons on the display."""
        # print("Initializing buttons")
        self.buttons = ButtonSet(self.wri, [name for name in self.screens.keys()])
        self.buttons.select_button(self.screen.name)
        refresh(ssd)

    async def display_loop(self, initial_screen):
        """Main loop for displaying data."""
        await self.switch_screen(initial_screen)
        while True:
            await self.screen.await_data()
            await self.screen.update_display()
            self.init_buttons()

    async def switch_screen(self, screen_name):
        """Switches to a different screen."""
        if screen_name in self.screens:
            self.screen = self.screens[screen_name]
            # print(f"Switching to screen {screen_name}")
        else:
            print(f"Screen {screen_name} not found")
        refresh(ssd, True)
        await self.screen.install()
        self.init_buttons()

    async def check_touch(self):
        """Checks for touch input and updates the selected button."""
        while True:
            t = touch.touch_get()
            if t:
                selection = self.buttons.check_touch(t)
                if selection:
                    # print(f"Switching to {selection}")
                    await self.switch_screen(selection)
                else:
                    await self.screen.handle_touch(t)
            await asyncio.sleep(0.01)

async def connect_network(console):
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    wlan.connect(NETWORK, PASSWORD)

    while not wlan.isconnected():
        await console.message("Waiting to connect")
        await asyncio.sleep(1)
    await console.message("Connected")

async def main():
    controller = DisplayController()
    console = controller.screens["console"]
    controls = JoystickController(ROVER, console)
    asyncio.create_task(controller.check_touch())
    asyncio.create_task(controller.display_loop("console"))
    await connect_network(console)
    asyncio.create_task(controls.watch_controls())

asyncio.run(main())
asyncio.get_event_loop().run_forever()

