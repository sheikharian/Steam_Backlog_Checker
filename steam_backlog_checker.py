# Steam Backlog Checker
# By: Sheikh Arian

import tkinter as tk
from tkinter import ttk, messagebox, Canvas, Scrollbar
from PIL import Image, ImageTk
import requests
from io import BytesIO
import threading

API_KEY = '#################'  # Replace with Steam API Key
image_refs = []  # Keep references to images

# get non-free game list from steam user
def get_owned_games(api_key, steam_id):
    url = 'https://api.steampowered.com/IPlayerService/GetOwnedGames/v1/'
    params = {
        'key': api_key,
        'steamid': steam_id,
        'include_appinfo': True,
        'include_played_free_games': False
    }
    response = requests.get(url, params=params)
    return response.json()

# filter games with <2 hours 
def filter_unplayed_games(games, max_hours=2):
    # returns list of games with basic info
    return [
        {
            'name': game['name'],
            'hours': round(game['playtime_forever'] / 60, 2),
            'appid': game['appid']
        }
        for game in games if game['playtime_forever'] / 60 < max_hours
    ]

# get game header image
def get_game_image(appid):
    url = f"https://cdn.akamai.steamstatic.com/steam/apps/{appid}/header.jpg"
    try:
        response = requests.get(url, timeout=5)
        response.raise_for_status()
        img_data = Image.open(BytesIO(response.content))
        img_data = img_data.resize((184, 69), Image.Resampling.LANCZOS) # resize image
        return ImageTk.PhotoImage(img_data)
    except Exception as e:
        print(f"[!] Image load failed for {appid}: {e}")
        return ImageTk.PhotoImage(Image.new('RGB', (184, 69), color='gray')) # if no image found, insert default gray box

# retrieve friend steam ids, requires public access to view friends list
def get_friend_ids(steam_id):
    url = 'https://api.steampowered.com/ISteamUser/GetFriendList/v1/'
    params = {'key': API_KEY, 'steamid': steam_id, 'relationship': 'friend'}
    response = requests.get(url, params=params)
    data = response.json()
    return [f['steamid'] for f in data.get('friendslist', {}).get('friends', [])]

# take list of friend steam ids and returns display names
def get_friend_names(steam_ids):
    url = 'https://api.steampowered.com/ISteamUser/GetPlayerSummaries/v2/'
    params = {'key': API_KEY, 'steamids': ','.join(steam_ids)}
    response = requests.get(url, params=params)
    data = response.json()
    return [
        {'steamid': p['steamid'], 'name': p['personaname']}
        for p in data['response'].get('players', [])
    ]

# fetches and displays a list of underplayed steam games for a given steam id
def fetch_and_display(steam_id):
    # clear previous results
    def clear_results():
        for widget in result_frame.winfo_children():
            widget.destroy()
    root.after(0, clear_results)

    try:
        data = get_owned_games(API_KEY, steam_id)
        if 'response' in data and 'games' in data['response']:
            games = data['response']['games']
            unplayed = filter_unplayed_games(games)
            image_data = []

            for game in sorted(unplayed, key=lambda g: g['hours']):
                img = get_game_image(game['appid'])
                image_refs.append(img)
                image_data.append((img, f"{game['name']} - {game['hours']} hrs"))
            
            # display backlog results
            def render():
                for img, label_text in image_data:
                    row = ttk.Frame(result_frame)
                    row.pack(anchor='w', pady=5)
                    if img:
                        img_label = ttk.Label(row, image=img)
                        img_label.image = img
                        img_label.pack(side='left', padx=5)
                    ttk.Label(row, text=label_text, wraplength=300, justify='left').pack(side='left')
                friend_button.pack(pady=10)

            root.after(0, render)
        else:
            root.after(0, lambda: ttk.Label(result_frame, text="No games found or profile is private.").pack())
    except Exception as e:
        root.after(0, lambda: messagebox.showerror("Error", f"Failed to fetch games:\n{e}"))

# checks entered steam id then starts thread on game library retrieval 
def on_check():
    steam_id = steam_id_entry.get().strip()
    if not steam_id:
        messagebox.showerror("Error", "Please enter your 64-bit SteamID.")
        return
    selected_friend_label.config(text="Viewing: You")
    friend_button.config(command=lambda: show_friend_list_popup(steam_id))
    threading.Thread(target=fetch_and_display, args=(steam_id,), daemon=True).start()

# creates pop-up window to view and select inputted steam id's friends
def show_friend_list_popup(steam_id):
    def load_friend(friend_id, friend_name):
        popup.destroy()
        root.after(0, lambda: selected_friend_label.config(text=f"Viewing: {friend_name}"))
        threading.Thread(target=fetch_and_display, args=(friend_id,), daemon=True).start()

    popup = tk.Toplevel(root)
    popup.title("Select a Friend")
    popup.geometry("300x400")

    listbox = tk.Listbox(popup)
    listbox.pack(fill='both', expand=True, padx=10, pady=10)

    status_label = ttk.Label(popup, text="Loading friend list...")
    status_label.pack()

    def load_friends():
        try:
            friend_ids = get_friend_ids(steam_id)
            if not friend_ids:
                root.after(0, lambda: status_label.config(text="No friends found or list is private."))
                return
            names = get_friend_names(friend_ids)
            name_id_map = {n['name']: n['steamid'] for n in names}
            sorted_names = sorted(name_id_map.keys())

            def populate():
                status_label.destroy()
                for name in sorted_names:
                    listbox.insert(tk.END, name)

                def on_select(event):
                    selection = listbox.get(listbox.curselection())
                    steam_id = name_id_map[selection]
                    load_friend(steam_id, selection)

                listbox.bind('<<ListboxSelect>>', on_select)

            root.after(0, populate)
        except Exception as e:
            root.after(0, lambda: status_label.config(text=f"Error: {e}"))

    threading.Thread(target=load_friends, daemon=True).start()

# --- GUI Setup ---
root = tk.Tk()
root.title("Steam Backlog Checker")
root.geometry("700x650")

# main layout container
main_frame = ttk.Frame(root, padding=10)
main_frame.pack(fill='both', expand=True)

# steam id user input field
ttk.Label(main_frame, text="Enter your 64-bit SteamID:").pack(pady=(0, 5))
steam_id_entry = ttk.Entry(main_frame, width=40)
steam_id_entry.pack(pady=(0, 10))

# button to start backlog check
ttk.Button(main_frame, text="Check My Games", command=on_check).pack()

# button to show friends of inputted steam id
friend_button = ttk.Button(main_frame, text="View Friends")

# display text for whose library is being shown
selected_friend_label = ttk.Label(main_frame, text="")
selected_friend_label.pack(pady=(10, 5))

# scrollable canvas for results
canvas = Canvas(main_frame)
scroll_y = Scrollbar(main_frame, orient="vertical", command=canvas.yview)
result_frame = ttk.Frame(canvas)

# enables mousewheel scrolling
def _on_mousewheel(event):
    canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
canvas.bind_all("<MouseWheel>", _on_mousewheel)
canvas.bind_all("<Button-4>", lambda e: canvas.yview_scroll(-1, "units"))
canvas.bind_all("<Button-5>", lambda e: canvas.yview_scroll(1, "units"))

result_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
canvas.create_window((0, 0), window=result_frame, anchor="nw")
canvas.configure(yscrollcommand=scroll_y.set)

canvas.pack(side="left", fill="both", expand=True)
scroll_y.pack(side="right", fill="y")

root.mainloop()
