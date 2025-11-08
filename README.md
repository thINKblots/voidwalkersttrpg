# ⚔️ Voidwalkers - Procedurally Generated TTRPG

A fully procedural tabletop RPG powered by AI:
- **Claude Sonnet 4.5** generates story elements, world building, and narrative
- **Gemini 2.0** handles rules, mechanics, and combat systems

## Features

- 🎭 Dynamic character creation with AI-generated stats
- 🌍 Procedurally generated worlds, locations, NPCs, and quests
- ⚔️ Turn-based combat with AI-powered mechanics
- 🎲 Dice rolling and action adjudication
- 📖 Story logging and save/load functionality
- 🎮 Full gameplay loop with exploration, combat, and questing

## Local Development

### Prerequisites

- Python 3.8+
- Anthropic API key (for Claude Sonnet)
- Google Gemini API key

### Setup

1. Clone the repository:
```bash
git clone <your-repo-url>
cd tabletopRoleplay
```

2. Create a virtual environment:
```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Add your API keys to `.streamlit/secrets.toml`:
```toml
ANTHROPIC_API_KEY = "your-anthropic-key"
GEMINI_API_KEY = "your-gemini-key"
```

5. Run the app:
```bash
streamlit run app.py
```

## Deploy to Streamlit Community Cloud

### Step 1: Push to GitHub

1. Initialize git (if not already done):
```bash
git init
git add .
git commit -m "Initial commit"
```

2. Create a new repository on GitHub and push:
```bash
git remote add origin <your-repo-url>
git branch -M main
git push -u origin main
```

### Step 2: Deploy on Streamlit Cloud

1. Go to [share.streamlit.io](https://share.streamlit.io)
2. Sign in with GitHub
3. Click "New app"
4. Select your repository, branch (main), and main file (app.py)
5. Click "Advanced settings" → "Secrets"
6. Add your API keys in TOML format:
```toml
ANTHROPIC_API_KEY = "your-anthropic-key"
GEMINI_API_KEY = "your-gemini-key"
```
7. Click "Deploy!"

### Important Security Notes

- ⚠️ **NEVER** commit API keys to your repository
- The `.gitignore` file prevents `secrets.toml` from being committed
- Always use Streamlit secrets or environment variables for sensitive data

## How to Play

1. **Create Character**: Choose a name and class (Warrior, Mage, Rogue, etc.)
2. **Explore**: The AI generates a unique dark fantasy world for your adventure
3. **Take Actions**:
   - Explore areas to discover new locations
   - Meet NPCs with unique personalities
   - Engage in combat with procedurally generated enemies
   - Complete quests with moral complexity
4. **Combat**: Use Attack, Defend, or Flee actions in turn-based battles
5. **Save**: Your progress auto-saves and persists between sessions

## Game Mechanics

- **Character Stats**: HP, Strength, Dexterity, Intelligence, Charisma, Defense
- **Dice System**: Standard d20 mechanics with modifiers
- **Combat**: AI-adjudicated turn-based battles
- **Actions**: Custom actions are interpreted and resolved by AI
- **Narration**: Every event is dramatically narrated by Claude Sonnet

## Technologies

- **Streamlit**: Web framework
- **Anthropic Claude Sonnet 4.5**: Story generation and narration
- **Google Gemini 2.0**: Game mechanics and rules engine
- **Python**: Backend logic

## License

MIT License - Feel free to use and modify!

## Contributing

Contributions welcome! Please open an issue or PR.

---

**Note**: This game requires API credits for both Anthropic and Google Gemini. Usage costs will vary based on gameplay.
# voidwalkersttrpg
# voidwalkersttrpg
# voidwalkersttrpg
# voidwalkersttrpg
