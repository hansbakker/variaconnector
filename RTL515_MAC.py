import tkinter as tk
import asyncio
from bleak import BleakScanner, BleakClient

service_uuid = "6a4e3200-667b-11e3-949a-0800200c9a66"
previous_threats = []
previous_id_byte = 0
existing_cars = {}  # Dictionary to track known cars by their number

# Window setup
root = tk.Tk()
root.title('RTL515 Bike Radar animation')
canvas = tk.Canvas(root, width=1200, height=200, bg='grey')
canvas.pack()
car_red = tk.PhotoImage(file='car_red.png')
car_yellow = tk.PhotoImage(file='car_yellow.png')
car_green = tk.PhotoImage(file='car_green.png')
bike = tk.PhotoImage(file='bike.png')
        

async def scan_for_rtl(): 
    devices = await BleakScanner.discover()
    for i, device in enumerate(devices):
        print(f"Device {i}: {device.name} ({device.address})")
        if device.name is not None and device.name[:3] == 'RTL':
            device_addr = device.address
            return device_addr
    return
    
async def tk_update():
    try:
        while True:
            root.update()  # Process Tkinter GUI events
            await asyncio.sleep(0.01)  # Briefly yield control to other asyncio tasks
    except tk.TclError as e:
        if "application has been destroyed" not in str(e):
            raise
            
def draw_road():
    # This is a simplified representation where the road is the entire canvas
    canvas.create_rectangle(0, 75, 1200, 125, fill='darkgrey')
    canvas.create_image(1200,110, image=bike, anchor='e')

def draw_or_update_car(number, distance, speed):
    posx = ((150-distance) / 150.0) * 1200
    #color is assigned only upon first detection of the care
    color = 'green' if speed <= 70 else ('yellow' if speed <= 100 else 'red')
    if number in existing_cars:
        # Update existing car's position 
        canvas.coords(existing_cars[number],posx,105)
    else:
        # Draw new car and store its ID in the dictionary
        if color == 'red':
            car_id = canvas.create_image(posx,105, image=car_red, anchor='e')
        elif color == 'yellow':
            car_id = canvas.create_image(posx,105, image=car_yellow, anchor='e')
        else:
            car_id = canvas.create_image(posx,105, image=car_green, anchor='e')
        existing_cars[number] = car_id

def update_cars(current_threats):
    # Create a set of current threat numbers for easy lookup    
    current_numbers = set(threat['number'] for threat in current_threats)
    # Delete cars that are not in the current threats
    for number in list(existing_cars):
        if number not in current_numbers:
            canvas.delete(existing_cars.pop(number))    
    # Update existing cars and add new ones
    for threat in current_threats:
        draw_or_update_car(threat['number'], threat['distance'], threat['speed'])

        
# Function to process radar data, translated from C++
def process_radar_data(sender,data):
    global previous_threats, previous_id_byte
    id_byte = 0
    found_threats = (len(data) - 1) // 3
    if found_threats > 0:
        print("Threats found:", found_threats)    
    current_threats = []     	                	
    id_byte = data[0]
    # as there can only be 6 threats (and demo mode shows at some point 8 cars) in one message, 
    # repeating the previous message's content could be needed, using the id_byte to find such situation
    if (id_byte == previous_id_byte + 2) :
            current_threats.extend(previous_threats)
    for i in range(found_threats):
        threat_number = data[1 + (i * 3)]
        threat_distance = data[2 + (i * 3)]
        threat_speed = data[3 + (i * 3)]
        print(f"ID: {id_byte} Index: {i + 1}: {threat_number} Threat Distance: {threat_distance} Speed: {threat_speed}")
        current_threat = {"number": threat_number, "distance": threat_distance, "speed": threat_speed}
        current_threats.append(current_threat)
    previous_id_byte = id_byte;
    previous_threats = current_threats;
    # update display
    update_cars(current_threats)    
    return 

async def main():    
    print("Scanning for BLE devices...")
    device_addr = await scan_for_rtl()
    if not device_addr:
        print("No devices found. Exiting...")
        return
    else:
        print(f"Connecting to {device_addr}")
    async with BleakClient(device_addr) as client:
        print(f"Connected to {device_addr}")

        # Ensuring the device offers the needed service
        services = await client.get_services()
        # garmin_service = services.get_service(service_uuid)
        if services.get_service(service_uuid) is None:
            print("Radar service not found. Exiting...")
            return
        draw_road()       
        # the characteristic UUID for threat data
        characteristic_uuid = "6a4e3203-667b-11e3-949a-0800200c9a66"
        await client.start_notify(characteristic_uuid, process_radar_data)
        
        print("Monitoring threats. Press Ctrl+C to exit.")
        while True:
            await asyncio.sleep(1)  # Keep the program running.
            # After setting up BLE and starting notifications:
            task_gui = asyncio.create_task(tk_update())  # Start the Tkinter update task
            await task_gui  # Wait for the Tkinter task to complete (e.g., window closed)

if __name__ == "__main__":
    asyncio.run(main())
