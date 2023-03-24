import os
import slippi
import json
import concurrent.futures
import threading
import tkinter as tk
from slippi.parse import ParseError
from tkinter import filedialog


#TODO
#Get just one json per falcon Punch -  DONE
#Have it write out the JSON
#Have it do it for every slp file in a directory
#Create UI

def find_captain_falcon_ports(replay, netplay_id):
    CAPTAIN_FALCON_ID = 0
    falcon_ports = []

    for port_idx, port in enumerate(replay.start.players):
        if port is not None and port.character == CAPTAIN_FALCON_ID:
            falcon_ports.append(port_idx)

    for port_idx, port in enumerate(replay.metadata.players):
        if port is not None and port.netplay is not None and port.netplay.name != netplay_id:
            falcon_ports = [elem for elem in falcon_ports if elem != port_idx]

    return falcon_ports


def falcon_punch_connected(replay, falcon_ports, filepath):
    start_offset = -120
    end_offset = 60
    FALCON_PUNCH_ATTACK_ID = 18
    HITLAG_FLAG_VALUE = 8256
    falcon_punches = []
    recorded_frames = set()

    # Loop through all frames in the game
    for frame in replay.frames:
        # Loop through Captain Falcon ports
        for port_idx in falcon_ports:
            port = frame.ports[port_idx]
            if port is not None:
                # Get the character being controlled by the port
                character = port.leader

                # Check if the attack ID of Falcon Punch (18) was ever the last attack landed
                if (character.post.last_attack_landed == FALCON_PUNCH_ATTACK_ID 
                    and frame.index not in recorded_frames):

                    # Find the opponent's port index
                    opponent_port_idx = (port_idx + 1) % 2
                    opponent_port = frame.ports[opponent_port_idx]
                    opponent = opponent_port.leader
                    
                    # Extract pre and post damage information
                    pre_damage = opponent.pre.damage
                    post_damage = opponent.post.damage
                    if post_damage - pre_damage > 22:
                    

                        falcon_punches.append({
                            "path": filepath,
                            "gameStartAt": replay.metadata.date.isoformat(),
                            "startFrame": max(0, frame.index + start_offset),
                            "endFrame": frame.index + end_offset
                        })
                        # Marks the other hitlag frames as duplicates.
                        for i in range(0, 20):
                            recorded_frames.add(frame.index + i)

    return falcon_punches

def browse_folder():
    folder_path = filedialog.askdirectory()
    folder_var.set(folder_path)

def browse_output_file():
    output_file_path = filedialog.asksaveasfilename(defaultextension=".json")
    output_file_var.set(output_file_path)

def process_file(filepath, netplay_id):
    try:
        replay = slippi.Game(filepath)
        falcon_ports = find_captain_falcon_ports(replay, netplay_id)
        return falcon_punch_connected(replay, falcon_ports, filepath)
    except ParseError as e:
        print(f"Error processing file '{filepath}': {e}")
        return []

def process_files():
    def process_files_thread():
        replay_directory = folder_var.get()
        connected_falcon_punches = []

        include_subdirs = include_subdirs_var.get()

        # Get the list of .slp files in the directory
        slp_files = []
        if include_subdirs:
            for root, _, files in os.walk(replay_directory):
                for file in files:
                    if file.endswith(".slp"):
                        slp_files.append(os.path.join(root, file))
        else:
            slp_files = [os.path.join(replay_directory, f) for f in os.listdir(replay_directory) if f.endswith(".slp")]


        total_files = len(slp_files)
        processed_files = 0

        netplay_id = netplay_id_var.get()

        # Process the files concurrently using a thread pool
        with concurrent.futures.ThreadPoolExecutor() as executor:
            for result in executor.map(lambda filepath: process_file(filepath, netplay_id), slp_files):
                connected_falcon_punches.extend(result)

                processed_files += 1
                progress_var.set(f"Processed {processed_files}/{total_files} replays")


        queue = {
            "mode": "queue",
            "replay": "",
            "isRealTimeMode": False,
            "outputOverlayFiles": True,
            "queue": connected_falcon_punches
        }

        json_output = json.dumps(queue, indent=2)

        with open(output_file_var.get(), "w") as json_file:
            json_file.write(json_output)

        output_var.set("JSON file created:" + output_file_var.get())

    t = threading.Thread(target=process_files_thread)
    t.start()

# Create the main window
root = tk.Tk()
root.title("Falcon Punch Finder")

# Create a label and entry for the folder path
folder_label = tk.Label(root, text="Replay folder:")
folder_label.grid(row=0, column=0, padx=10, pady=10, sticky="w")
folder_var = tk.StringVar()
folder_entry = tk.Entry(root, textvariable=folder_var, width=50)
folder_entry.grid(row=0, column=1, padx=10, pady=10)

# Create a button to browse for a folder
browse_button = tk.Button(root, text="Browse", command=browse_folder)
browse_button.grid(row=0, column=2, padx=10, pady=10)
include_subdirs_var = tk.BooleanVar()
include_subdirs_checkbox = tk.Checkbutton(root, text="Include Subdirectories", variable=include_subdirs_var)
include_subdirs_checkbox.grid(row=0, column=3, padx=10, pady=10)

# Create a label and entry for the output file path
output_file_label = tk.Label(root, text="Output file:")
output_file_label.grid(row=1, column=0, padx=10, pady=10, sticky="w")
output_file_var = tk.StringVar()
output_file_entry = tk.Entry(root, textvariable=output_file_var, width=50)
output_file_entry.grid(row=1, column=1, padx=10, pady=10)

# Create a button to browse for an output file
output_browse_button = tk.Button(root, text="Browse", command=browse_output_file)
output_browse_button.grid(row=1, column=2, padx=10, pady=10)

# Create a label and entry for the NetplayID
netplay_id_label = tk.Label(root, text="Netplay ID:")
netplay_id_label.grid(row=2, column=0, padx=10, pady=10, sticky="w")
netplay_id_var = tk.StringVar(value="OGMilkbone")
netplay_id_entry = tk.Entry(root, textvariable=netplay_id_var, width=50)
netplay_id_entry.grid(row=2, column=1, padx=10, pady=10)

# Create a button to process the files
process_button = tk.Button(root, text="Process Files", command=process_files)
process_button.grid(row=3, column=1, padx=10, pady=10)

# Create a label for the output message
output_var = tk.StringVar()
output_label = tk.Label(root, textvariable=output_var)
output_label.grid(row=4, column=0, columnspan=3, padx=10, pady=10)

# Create a label for the progress message
progress_var = tk.StringVar()
progress_label = tk.Label(root, textvariable=progress_var)
progress_label.grid(row=5, column=0, columnspan=3, padx=10, pady=10)

# Run the main loop
root.mainloop()