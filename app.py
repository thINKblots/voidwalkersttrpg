"""
Voidwalkers - A Procedurally Generated TTRPG
Uses Claude Sonnet 4.5 for story elements and world building
Uses Gemini 2.5 Pro for rules, dice rolling, and mechanics
"""

import anthropic
import google.generativeai as genai
from google.cloud import texttospeech
import streamlit as st
import random
import json
import os
import base64
from datetime import datetime
from typing import List, Dict, Optional

# Initialize clients for Sonnet and Gemini
# Try to get API keys from Streamlit secrets first, then environment variables
try:
    ANTHROPIC_API_KEY = st.secrets["ANTHROPIC_API_KEY"]
    GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"]

    # Handle Google Cloud credentials from Streamlit secrets for deployment
    if "GOOGLE_APPLICATION_CREDENTIALS_JSON" in st.secrets:
        import tempfile
        import json as json_lib
        # Write credentials to a temporary file
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
            json_lib.dump(dict(st.secrets["GOOGLE_APPLICATION_CREDENTIALS_JSON"]), f)
            os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = f.name
except:
    # Fallback to environment variables for local development
    ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if not ANTHROPIC_API_KEY or not GEMINI_API_KEY:
    st.error("⚠️ API keys not configured! Please add ANTHROPIC_API_KEY and GEMINI_API_KEY to your Streamlit secrets or environment variables.")
    st.stop()

sonnet_client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
genai.configure(api_key=GEMINI_API_KEY)
gemini_client = genai.GenerativeModel('gemini-2.0-flash-exp')

# Initialize Google Cloud Text-to-Speech client
# Note: This uses GOOGLE_APPLICATION_CREDENTIALS env var or default credentials
try:
    tts_client = texttospeech.TextToSpeechClient()
except Exception as e:
    st.warning(f"⚠️ Google Cloud TTS not configured. TTS features will be unavailable. Error: {str(e)}")
    tts_client = None

# Initialize session state
def get_default_game_state():
    return {
        "character": None,
        "current_location": None,
        "inventory": [],
        "npcs": [],
        "locations": [],
        "quests": [],
        "combat_log": [],
        "story_log": [],
        "game_started": False,
        "current_encounter": None,
        "world_context": "",
        "tts_enabled": False
    }

if 'game_state' not in st.session_state:
    if os.path.exists("game_state.json"):
        try:
            with open("game_state.json", "r") as f:
                loaded_state = json.load(f)
                # Validate that it has the required keys
                default_state = get_default_game_state()
                if "character" in loaded_state and "current_location" in loaded_state:
                    st.session_state.game_state = loaded_state
                else:
                    # Old format, use default
                    st.session_state.game_state = default_state
        except:
            st.session_state.game_state = get_default_game_state()
    else:
        st.session_state.game_state = get_default_game_state()

def get_game_state():
    """Helper function to safely get game state"""
    return st.session_state.game_state

def save_game_state(filename: str = "game_state.json"):
    """Save game state to a specific file"""
    with open(filename, "w") as f:
        json.dump(st.session_state.game_state, f, indent=2)

def load_game_state(filename: str = "game_state.json"):
    """Load game state from a specific file"""
    if os.path.exists(filename):
        try:
            with open(filename, "r") as f:
                loaded_state = json.load(f)
                if "character" in loaded_state and "current_location" in loaded_state:
                    st.session_state.game_state = loaded_state
                    return True
        except:
            pass
    return False

def get_save_files():
    """Get list of all save game files"""
    import glob
    saves = glob.glob("*.json")
    # Filter to only game save files (those with character data)
    game_saves = []
    for save in saves:
        try:
            with open(save, "r") as f:
                data = json.load(f)
                if "character" in data and data["character"]:
                    game_saves.append(save)
        except:
            pass
    return game_saves

def log_story(event: str):
    timestamp = datetime.now().strftime("%H:%M:%S")
    st.session_state.game_state["story_log"].append(f"[{timestamp}] {event}")
    save_game_state()

def log_combat(event: str):
    timestamp = datetime.now().strftime("%H:%M:%S")
    st.session_state.game_state["combat_log"].append(f"[{timestamp}] {event}")
    save_game_state()

# Create audio cache directory
AUDIO_CACHE_DIR = "audio_cache"
if not os.path.exists(AUDIO_CACHE_DIR):
    os.makedirs(AUDIO_CACHE_DIR)

def generate_tts_audio(text: str, text_hash: str) -> str:
    """Generate audio using Google Cloud TTS and cache it"""
    import hashlib

    if tts_client is None:
        raise Exception("TTS client not initialized. Please configure Google Cloud credentials.")

    cache_file = os.path.join(AUDIO_CACHE_DIR, f"{text_hash}.mp3")

    # Return cached audio if it exists
    if os.path.exists(cache_file):
        return cache_file

    # Clean text for speech (remove markdown formatting)
    clean_text = text.replace('**', '').replace('*', '').replace('#', '').replace('_', '')

    # Configure the TTS request
    synthesis_input = texttospeech.SynthesisInput(text=clean_text)

    # Build the voice request - using a high-quality neural voice
    voice = texttospeech.VoiceSelectionParams(
        language_code="en-US",
        name="en-US-Neural2-D",  # Natural, conversational male voice
        ssml_gender=texttospeech.SsmlVoiceGender.MALE
    )

    # Select the audio encoding
    audio_config = texttospeech.AudioConfig(
        audio_encoding=texttospeech.AudioEncoding.MP3,
        speaking_rate=0.95,  # Slightly slower for better clarity
        pitch=0.0,
        volume_gain_db=0.0
    )

    # Perform the text-to-speech request
    response = tts_client.synthesize_speech(
        input=synthesis_input,
        voice=voice,
        audio_config=audio_config
    )

    # Save the audio to cache
    with open(cache_file, "wb") as out:
        out.write(response.audio_content)

    return cache_file

def speak_text(text: str, button_key: str):
    """Display text with a TTS button using Google Cloud TTS"""
    import hashlib

    # Create unique key for this text
    text_hash = hashlib.md5(text.encode()).hexdigest()[:8]
    unique_key = f"tts_{button_key}_{text_hash}"

    col1, col2 = st.columns([0.95, 0.05])

    with col1:
        st.markdown(text)

    with col2:
        # Create button that triggers TTS
        if st.button("🔊", key=unique_key, help="Read aloud"):
            try:
                # Generate or retrieve cached audio
                audio_file = generate_tts_audio(text, text_hash)

                # Read the audio file and encode as base64
                with open(audio_file, "rb") as f:
                    audio_bytes = f.read()
                    audio_base64 = base64.b64encode(audio_bytes).decode()

                # Display audio player
                audio_html = f"""
                <audio autoplay>
                    <source src="data:audio/mp3;base64,{audio_base64}" type="audio/mp3">
                </audio>
                """
                st.markdown(audio_html, unsafe_allow_html=True)
            except Exception as e:
                st.error(f"TTS Error: {str(e)}")

# ============== DICE ROLLING & MECHANICS (GEMINI) ==============
def roll_dice(dice_notation: str) -> Dict:
    """Roll dice and return results (e.g., '2d6', '1d20+5')"""
    parts = dice_notation.lower().replace(" ", "").split('d')
    num_dice = int(parts[0]) if parts[0] else 1

    modifier = 0
    if '+' in parts[1]:
        die_size, mod = parts[1].split('+')
        modifier = int(mod)
    elif '-' in parts[1]:
        die_size, mod = parts[1].split('-')
        modifier = -int(mod)
    else:
        die_size = parts[1]

    die_size = int(die_size)
    rolls = [random.randint(1, die_size) for _ in range(num_dice)]
    total = sum(rolls) + modifier

    return {
        "notation": dice_notation,
        "rolls": rolls,
        "modifier": modifier,
        "total": total
    }

def adjudicate_action(action: str, character_stats: Dict, difficulty: str) -> Dict:
    """Use Gemini to adjudicate player actions based on rules"""
    prompt = f"""You are the rules engine for a fantasy TTRPG. Adjudicate this action:

Action: {action}
Character Stats: {json.dumps(character_stats)}
Difficulty: {difficulty}

Provide a JSON response with:
1. required_roll: What dice to roll (e.g., "1d20")
2. difficulty_class: Target number to beat
3. relevant_stat: Which stat applies
4. success_threshold: Description of success/failure
5. special_rules: Any special mechanics that apply

Return ONLY valid JSON, no markdown formatting."""

    response = gemini_client.generate_content(prompt)
    try:
        return json.loads(response.text.strip().replace('```json', '').replace('```', ''))
    except:
        return {
            "required_roll": "1d20",
            "difficulty_class": 10,
            "relevant_stat": "any",
            "success_threshold": "Roll 10+ to succeed",
            "special_rules": "Standard check"
        }

# ============== CHARACTER CREATION ==============
def create_character(name: str, character_class: str) -> Dict:
    """Use Gemini to generate balanced character stats"""
    prompt = f"""Generate starting stats for a {character_class} character named {name} in a fantasy TTRPG.

Use this stat system:
- HP (Health Points): 20-50
- Strength: 1-10
- Dexterity: 1-10
- Intelligence: 1-10
- Charisma: 1-10
- Defense: 5-15

Provide 3 starting abilities appropriate to the class.

Return ONLY valid JSON with this structure:
{{
  "name": "{name}",
  "class": "{character_class}",
  "level": 1,
  "hp": number,
  "max_hp": number,
  "strength": number,
  "dexterity": number,
  "intelligence": number,
  "charisma": number,
  "defense": number,
  "abilities": ["ability1", "ability2", "ability3"]
}}"""

    response = gemini_client.generate_content(prompt)
    try:
        character = json.loads(response.text.strip().replace('```json', '').replace('```', ''))
        return character
    except:
        return {
            "name": name,
            "class": character_class,
            "level": 1,
            "hp": 30,
            "max_hp": 30,
            "strength": 5,
            "dexterity": 5,
            "intelligence": 5,
            "charisma": 5,
            "defense": 10,
            "abilities": ["Basic Attack", "Defend", "Focus"]
        }

# ============== WORLD BUILDING (SONNET) ==============
def generate_world_intro() -> str:
    """Generate initial world setting and premise"""
    prompt = """You are a creative game master for a dark fantasy TTRPG called Voidwalkers.

Generate an intriguing opening that:
1. Describes a unique, atmospheric fantasy world
2. Establishes a mysterious threat or conflict
3. Sets the stage for adventure
4. Is 3-4 paragraphs, vivid and immersive

Make it compelling and mysterious."""

    message = sonnet_client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=1500,
        messages=[{"role": "user", "content": prompt}]
    )
    return message.content[0].text

def generate_location(location_type: str, context: str) -> Dict:
    """Generate a new location with Sonnet"""
    prompt = f"""Generate a {location_type} location for a dark fantasy TTRPG.

World Context: {context}

Provide:
1. Name of the location
2. Vivid description (2-3 paragraphs)
3. 2-3 points of interest
4. Potential dangers or mysteries
5. Notable NPCs that might be here

Be creative and atmospheric."""

    message = sonnet_client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=1500,
        messages=[{"role": "user", "content": prompt}]
    )

    description = message.content[0].text

    # Extract a name from the description (simple approach)
    lines = description.split('\n')
    name = lines[0].strip('#* ') if lines else f"The {location_type.title()}"

    location = {
        "name": name,
        "type": location_type,
        "description": description,
        "visited": False
    }

    st.session_state.game_state["locations"].append(location)
    log_story(f"Discovered new location: {name}")
    save_game_state()
    return location

def generate_npc(role: str, location: str) -> Dict:
    """Generate an NPC with Sonnet"""
    prompt = f"""Create an NPC for a dark fantasy TTRPG.

Role: {role}
Location: {location}
World: Voidwalkers - a world threatened by mysterious void creatures

Provide:
1. Name
2. Appearance and personality (2 paragraphs)
3. A secret or hidden motivation
4. How they might help or hinder the player

Be memorable and nuanced."""

    message = sonnet_client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=1200,
        messages=[{"role": "user", "content": prompt}]
    )

    description = message.content[0].text
    lines = description.split('\n')
    name = lines[0].strip('#* ') if lines else f"The {role}"

    npc = {
        "name": name,
        "role": role,
        "location": location,
        "description": description,
        "disposition": "neutral"
    }

    st.session_state.game_state["npcs"].append(npc)
    log_story(f"Met {name}, a {role}")
    save_game_state()
    return npc

def generate_quest(context: str) -> Dict:
    """Generate a quest with Sonnet"""
    prompt = f"""Create a quest for a dark fantasy TTRPG.

Current Context: {context}

Generate:
1. Quest title
2. Quest giver or hook
3. Objective
4. Potential complications
5. Rewards

Make it engaging with moral complexity."""

    message = sonnet_client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=1200,
        messages=[{"role": "user", "content": prompt}]
    )

    description = message.content[0].text
    lines = description.split('\n')
    title = lines[0].strip('#* ') if lines else "A New Quest"

    quest = {
        "title": title,
        "description": description,
        "status": "active",
        "objectives": []
    }

    st.session_state.game_state["quests"].append(quest)
    log_story(f"New quest: {title}")
    save_game_state()
    return quest

# ============== ENCOUNTERS & COMBAT ==============
def generate_encounter(encounter_type: str, character_level: int) -> Dict:
    """Use Gemini to generate balanced combat encounters"""
    prompt = f"""Generate a {encounter_type} encounter for a level {character_level} character in a dark fantasy setting.

Include:
1. Enemy name and description
2. Stats (HP: 20-80, Attack: 5-20, Defense: 5-15)
3. Special abilities (1-2)
4. Tactics or behavior patterns

Return ONLY valid JSON:
{{
  "name": "enemy name",
  "description": "description",
  "hp": number,
  "max_hp": number,
  "attack": number,
  "defense": number,
  "abilities": ["ability1"],
  "loot": ["item1", "item2"]
}}"""

    response = gemini_client.generate_content(prompt)
    try:
        encounter = json.loads(response.text.strip().replace('```json', '').replace('```', ''))
        return encounter
    except:
        return {
            "name": "Void Creature",
            "description": "A shadowy beast from the void",
            "hp": 30,
            "max_hp": 30,
            "attack": 10,
            "defense": 8,
            "abilities": ["Shadow Strike"],
            "loot": ["Void Essence"]
        }

def narrate_event(event: str, context: str) -> str:
    """Use Sonnet to narrate game events dramatically"""
    prompt = f"""You are the narrator for a dark fantasy TTRPG called Voidwalkers.

Event: {event}
Context: {context}

Narrate this event in 2-3 vivid, atmospheric sentences. Make it engaging and immersive."""

    message = sonnet_client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=500,
        messages=[{"role": "user", "content": prompt}]
    )
    return message.content[0].text

def process_combat_round(player_action: str, enemy: Dict, character: Dict) -> str:
    """Use Gemini for combat mechanics"""
    prompt = f"""Process a combat round in a fantasy TTRPG.

Player Action: {player_action}
Player Stats: {json.dumps(character)}
Enemy Stats: {json.dumps(enemy)}

Determine:
1. Does player hit? (roll 1d20 + relevant stat vs enemy defense)
2. Damage dealt (if hit)
3. Enemy response/counterattack
4. Damage to player (if any)
5. Updated HP for both

Return ONLY valid JSON:
{{
  "player_hit": boolean,
  "player_damage": number,
  "enemy_damage": number,
  "player_hp": number,
  "enemy_hp": number,
  "description": "what happened"
}}"""

    response = gemini_client.generate_content(prompt)
    try:
        result = json.loads(response.text.strip().replace('```json', '').replace('```', ''))
        return result
    except:
        return {
            "player_hit": True,
            "player_damage": random.randint(5, 15),
            "enemy_damage": random.randint(3, 10),
            "player_hp": character['hp'] - random.randint(3, 10),
            "enemy_hp": enemy['hp'] - random.randint(5, 15),
            "description": "You exchange blows with the enemy!"
        }

# ============== STREAMLIT UI ==============
st.set_page_config(page_title="Voidwalkers TTRPG", layout="wide")
st.title("⚔️ Voidwalkers - Procedurally Generated TTRPG")

# Get game state reference
game_state = st.session_state.game_state

# Sidebar - Character Sheet
with st.sidebar:
    st.header("Character Sheet")

    if game_state["character"]:
        char = game_state["character"]
        st.subheader(f"{char['name']}")
        st.write(f"**Class:** {char['class']} (Level {char['level']})")

        # Health bar
        hp_percent = (char['hp'] / char['max_hp']) * 100
        st.progress(hp_percent / 100)
        st.write(f"HP: {char['hp']}/{char['max_hp']}")

        # Stats
        st.write("**Stats:**")
        col1, col2 = st.columns(2)
        with col1:
            st.metric("STR", char['strength'])
            st.metric("DEX", char['dexterity'])
            st.metric("INT", char['intelligence'])
        with col2:
            st.metric("CHA", char['charisma'])
            st.metric("DEF", char['defense'])

        st.write("**Abilities:**")
        for ability in char.get('abilities', []):
            st.write(f"• {ability}")

        st.divider()

        # Save/Load Section
        st.subheader("💾 Save & Load")

        # Save game
        save_name = st.text_input("Save name:", value=char['name'], key="save_name_input")
        col_save, col_load = st.columns(2)

        with col_save:
            if st.button("💾 Save", use_container_width=True):
                if save_name:
                    filename = f"{save_name.replace(' ', '_')}.json"
                    save_game_state(filename)
                    st.success(f"Saved to {filename}!")
                else:
                    st.error("Enter a save name!")

        # Load game
        with col_load:
            if st.button("📂 Load", use_container_width=True):
                st.session_state['show_load_menu'] = True

        # Show load menu
        if st.session_state.get('show_load_menu', False):
            save_files = get_save_files()
            if save_files:
                st.write("**Select save file:**")
                for save_file in save_files:
                    col1, col2 = st.columns([3, 1])
                    with col1:
                        # Extract character info
                        try:
                            with open(save_file, "r") as f:
                                data = json.load(f)
                                char_info = f"{data['character']['name']} - Lv{data['character']['level']} {data['character']['class']}"
                                st.write(f"📄 {save_file}: {char_info}")
                        except:
                            st.write(f"📄 {save_file}")
                    with col2:
                        if st.button("Load", key=f"load_{save_file}"):
                            if load_game_state(save_file):
                                st.success(f"Loaded {save_file}!")
                                st.session_state['show_load_menu'] = False
                                st.rerun()
                            else:
                                st.error("Failed to load!")

                if st.button("❌ Cancel"):
                    st.session_state['show_load_menu'] = False
                    st.rerun()
            else:
                st.info("No save files found")
                if st.button("Close"):
                    st.session_state['show_load_menu'] = False
                    st.rerun()

        st.divider()

        if st.button("🔄 New Game"):
            st.session_state.game_state = {
                "character": None,
                "current_location": None,
                "inventory": [],
                "npcs": [],
                "locations": [],
                "quests": [],
                "combat_log": [],
                "story_log": [],
                "game_started": False,
                "current_encounter": None,
                "world_context": ""
            }
            save_game_state()
            st.rerun()
    else:
        st.info("Create a character to begin")

# Main Game Area
if not game_state["character"]:
    # Character Creation
    st.header("🎭 Create Your Character")

    tab_create, tab_load = st.tabs(["✨ New Game", "📂 Load Game"])

    with tab_create:
        st.subheader("Start a New Adventure")

        col1, col2 = st.columns(2)

        with col1:
            char_name = st.text_input("Character Name", placeholder="Enter name...")

        with col2:
            char_class = st.selectbox("Class", [
                "Warrior",
                "Mage",
                "Rogue",
                "Cleric",
                "Ranger",
                "Paladin"
            ])

        if st.button("⚔️ Begin Adventure", type="primary"):
            if char_name:
                with st.spinner("Creating character and generating world..."):
                    # Create character
                    character = create_character(char_name, char_class)
                    game_state["character"] = character

                    # Generate world intro
                    world_intro = generate_world_intro()
                    game_state["world_context"] = world_intro
                    game_state["game_started"] = True

                    # Generate starting location
                    starting_location = generate_location("village", world_intro)
                    game_state["current_location"] = starting_location["name"]

                    log_story(f"{char_name} the {char_class} begins their journey")
                    save_game_state()

                st.success("Character created! Your adventure begins...")
                st.rerun()
            else:
                st.error("Please enter a character name")

    with tab_load:
        st.subheader("Load a Saved Game")

        save_files = get_save_files()
        if save_files:
            for save_file in save_files:
                with st.container():
                    try:
                        with open(save_file, "r") as f:
                            data = json.load(f)
                            char_data = data['character']

                            col1, col2, col3 = st.columns([3, 2, 1])

                            with col1:
                                st.write(f"**{char_data['name']}**")
                                st.caption(f"Level {char_data['level']} {char_data['class']}")

                            with col2:
                                st.write(f"HP: {char_data['hp']}/{char_data['max_hp']}")
                                st.caption(f"Location: {data.get('current_location', 'Unknown')}")

                            with col3:
                                if st.button("Load", key=f"main_load_{save_file}", type="primary"):
                                    if load_game_state(save_file):
                                        st.success(f"Loaded {save_file}!")
                                        st.rerun()
                                    else:
                                        st.error("Failed to load!")

                            st.divider()
                    except Exception as e:
                        st.error(f"Error reading {save_file}: {str(e)}")
        else:
            st.info("No saved games found. Create a new character to begin!")

else:
    # Main Game Interface
    tab1, tab2, tab3, tab4 = st.tabs(["🎮 Adventure", "📖 Story Log", "🗡️ Combat", "📜 Quests"])

    with tab1:
        st.header("Current Adventure")

        # Display world context
        if game_state["world_context"] and not game_state.get("world_shown", False):
            st.markdown("### 🌍 Welcome to Voidwalkers")
            speak_text(game_state["world_context"], "world_intro")
            game_state["world_shown"] = True
            save_game_state()

        # Current location
        if game_state["current_location"]:
            st.subheader(f"📍 Current Location: {game_state['current_location']}")

            current_loc = next((loc for loc in game_state["locations"]
                              if loc["name"] == game_state["current_location"]), None)
            if current_loc:
                speak_text(current_loc["description"], f"location_{game_state['current_location']}")

        st.divider()

        # Actions
        st.subheader("What do you do?")

        col1, col2, col3 = st.columns(3)

        with col1:
            if st.button("🗺️ Explore Area"):
                with st.spinner("Exploring..."):
                    location_types = ["ruins", "forest", "cave", "shrine", "dungeon"]
                    new_loc = generate_location(
                        random.choice(location_types),
                        game_state["world_context"]
                    )
                    st.success(f"You discovered: {new_loc['name']}")
                    speak_text(new_loc["description"], f"new_location_{new_loc['name']}")

        with col2:
            if st.button("👥 Meet Someone"):
                with st.spinner("Encountering..."):
                    roles = ["merchant", "wanderer", "cultist", "guard", "mysterious figure"]
                    npc = generate_npc(
                        random.choice(roles),
                        game_state["current_location"]
                    )
                    st.success(f"You meet: {npc['name']}")
                    speak_text(npc["description"], f"npc_{npc['name']}")

        with col3:
            if st.button("⚔️ Seek Combat"):
                with st.spinner("Searching for enemies..."):
                    char_level = game_state["character"]["level"]
                    encounter = generate_encounter("combat", char_level)
                    game_state["current_encounter"] = encounter

                    narration = narrate_event(
                        f"encountered a {encounter['name']}",
                        game_state["current_location"]
                    )

                    st.warning(f"⚔️ Combat Initiated!")
                    # Combine narration and description for TTS
                    combat_intro = f"{narration}\n\n{encounter['name']}. {encounter['description']}"
                    speak_text(combat_intro, f"combat_encounter_{encounter['name']}")

                    log_combat(f"Encountered {encounter['name']}")
                    save_game_state()

        # Custom Action
        st.divider()
        custom_action = st.text_input("Or describe your own action:",
                                      placeholder="I search for hidden passages...")

        if st.button("🎲 Perform Action"):
            if custom_action:
                with st.spinner("Processing action..."):
                    # Use Gemini to adjudicate
                    judgment = adjudicate_action(
                        custom_action,
                        game_state["character"],
                        "medium"
                    )

                    st.write(f"**Action:** {custom_action}")
                    st.write(f"**Required:** {judgment['required_roll']} vs DC {judgment['difficulty_class']}")

                    # Roll dice
                    roll_result = roll_dice(judgment['required_roll'])
                    st.write(f"**Roll:** {roll_result['rolls']} = **{roll_result['total']}**")

                    # Determine success
                    success = roll_result['total'] >= judgment['difficulty_class']

                    if success:
                        # Use Sonnet to narrate success
                        narration = narrate_event(
                            f"successfully {custom_action}",
                            game_state["current_location"]
                        )
                        st.success("✅ Success!")
                        speak_text(narration, f"action_success_{roll_result['total']}")
                    else:
                        narration = narrate_event(
                            f"failed to {custom_action}",
                            game_state["current_location"]
                        )
                        st.error("❌ Failure!")
                        speak_text(narration, f"action_failure_{roll_result['total']}")

                    log_story(f"{custom_action} - {'Success' if success else 'Failure'}")
                    save_game_state()

    with tab2:
        st.header("📖 Story Log")

        if game_state["story_log"]:
            for log in reversed(game_state["story_log"][-20:]):
                st.write(log)
        else:
            st.info("Your story has just begun...")

    with tab3:
        st.header("🗡️ Combat")

        if game_state["current_encounter"]:
            enemy = game_state["current_encounter"]
            char = game_state["character"]

            col1, col2 = st.columns(2)

            with col1:
                st.subheader(f"👤 {char['name']}")
                st.progress(char['hp'] / char['max_hp'])
                st.write(f"HP: {char['hp']}/{char['max_hp']}")

            with col2:
                st.subheader(f"👹 {enemy['name']}")
                st.progress(enemy['hp'] / enemy['max_hp'])
                st.write(f"HP: {enemy['hp']}/{enemy['max_hp']}")

            st.divider()

            # Combat actions
            st.subheader("Choose your action:")

            col1, col2, col3 = st.columns(3)

            with col1:
                if st.button("⚔️ Attack"):
                    with st.spinner("Processing combat..."):
                        result = process_combat_round(
                            "attack",
                            enemy,
                            char
                        )

                        # Narrate the combat
                        combat_narration = narrate_event(
                            result["description"],
                            "in combat"
                        )

                        speak_text(combat_narration, f"combat_round_{result['player_hp']}_{result['enemy_hp']}")

                        # Update stats
                        game_state["character"]["hp"] = result["player_hp"]
                        game_state["current_encounter"]["hp"] = result["enemy_hp"]

                        # Check for victory/defeat
                        if result["enemy_hp"] <= 0:
                            st.success(f"🎉 Victory! You defeated the {enemy['name']}!")
                            if enemy.get("loot"):
                                st.write(f"**Loot:** {', '.join(enemy['loot'])}")
                                game_state["inventory"].extend(enemy["loot"])
                            game_state["current_encounter"] = None
                            log_combat(f"Defeated {enemy['name']}")
                        elif result["player_hp"] <= 0:
                            st.error("💀 You have been defeated!")
                            game_state["character"]["hp"] = 1
                            game_state["current_encounter"] = None
                            log_combat("Defeated in combat")

                        save_game_state()
                        st.rerun()

            with col2:
                if st.button("🛡️ Defend"):
                    with st.spinner("Defending..."):
                        damage = max(0, enemy["attack"] - char["defense"] - 5)
                        game_state["character"]["hp"] = max(0, char["hp"] - damage)

                        st.write(f"You raise your guard! Took {damage} damage.")
                        log_combat(f"Defended - took {damage} damage")
                        save_game_state()
                        st.rerun()

            with col3:
                if st.button("🏃 Flee"):
                    flee_roll = roll_dice("1d20")
                    if flee_roll["total"] >= 10:
                        st.success("You successfully fled from combat!")
                        game_state["current_encounter"] = None
                        log_combat("Fled from combat")
                        save_game_state()
                        st.rerun()
                    else:
                        st.error("Failed to flee! The enemy attacks!")
                        damage = enemy["attack"] - char["defense"]
                        game_state["character"]["hp"] -= damage
                        log_combat(f"Failed to flee - took {damage} damage")
                        save_game_state()
                        st.rerun()

            # Show combat log
            st.divider()
            st.subheader("Combat Log")
            for log in reversed(game_state["combat_log"][-10:]):
                st.write(log)

        else:
            st.info("No active combat. Seek enemies in the Adventure tab!")

    with tab4:
        st.header("📜 Quests")

        if st.button("✨ Generate New Quest"):
            with st.spinner("Generating quest..."):
                context = f"Character: {game_state['character']['name']}, Location: {game_state['current_location']}"
                quest = generate_quest(context)
                st.success(f"New Quest: {quest['title']}")
                speak_text(quest["description"], f"quest_{quest['title']}")

        st.divider()

        # Display active quests
        active_quests = [q for q in game_state["quests"] if q.get("status") == "active"]

        if active_quests:
            for quest in active_quests:
                with st.expander(f"📌 {quest['title']}"):
                    speak_text(quest["description"], f"active_quest_{quest['title']}")
                    if st.button(f"Complete Quest", key=quest["title"]):
                        quest["status"] = "completed"
                        st.success("Quest completed!")
                        save_game_state()
                        st.rerun()
        else:
            st.info("No active quests. Generate one to begin!")

