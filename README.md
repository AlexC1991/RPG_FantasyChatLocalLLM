```
       ,     
      / \    
     {   }       VOX-AI FANTASY CHAT
    p   !   q    -------------------
    k   :   ;    Your Gateway to Infinite Text Adventures
    l   :   ;    
     \  :  /     Powered by Local LLMs + RAG Memory
      \ : /      
       \:|       
        |        
       _|_   
```

# Welcome to VOX-AI Fantasy Chat

VOX-AI is a powerful, locally-hosted roleplaying interface designed to bring your fantasies to life. Using advanced Large Language Models (LLMs) running directly on your machine, it creates immersive, interactive stories where you are the hero (or villain).

**New in v2.0**: Infinite conversation length with RAG (Retrieval-Augmented Generation) - the AI now has **true long-term memory**!

---

## 🚀 Quick Start

1.  **Run the App**: Double-click `Start_Fantasy.bat` (or run `python app.py`).
2.  **Open Browser**: Go to `http://127.0.0.1:5000` (it should open automatically).
3.  **Create a Card**: Click the `+` button in the sidebar to create a new Fantasy Card.
4.  **Configure Settings**: Click the **Settings** button to set up your archive path and RAG preferences.
5.  **Start Chatting**: Select your card and begin your adventure!

---

## 🆕 What's New - Version 2.0

### 🧠 RAG Long-Term Memory
- **Infinite Conversations**: No more context limits! Chat for thousands of messages.
- **Smart Archiving**: Old messages are automatically archived when context fills up (default: 80% full).
- **Semantic Memory**: The AI can search through *all* past conversations and retrieve relevant context.
- **Automatic Retrieval**: When you reference old events, the AI automatically finds and recalls them.

### ⚙️ Settings Panel
- **Archive Configuration**: Choose where to save old conversations.
- **Context Window**: Adjust how much the AI remembers at once (2048-8192 tokens).
- **RAG Controls**: Enable/disable memory retrieval, adjust how many messages to retrieve (1-20).
- **Live Statistics**: See messages in RAM, total archived, RAG retrievals, and storage usage.

### 📝 Narrative Formatting
- **Bracket Notation**: Use `[action in brackets]` to create italicized narrative text in your messages.
- **Enhanced Readability**: Larger, clearer message bubbles with better contrast.
- **Five Themes**: Default, Dark, Blood, Forest, and Mystic themes for different moods.

---

## 🧠 How the AI Works

This application uses **Local LLMs** (Large Language Models) like Dolphin, Mistral, or Llama. These are AI brains that live on your computer, meaning:
*   **Privacy**: Your chats never leave your PC.
*   **Control**: You decide what is allowed.
*   **Cost**: Free to run (uses your hardware).

### The "Passion Level" (Temperature)
In the Fantasy Editor, you will see a slider called **Passion Level**. This controls how "creative" or "chaotic" the AI is.
*   **Tame (0.1 - 0.7)**: The AI is logical, consistent, and follows instructions strictly. Good for serious lore or complex plots.
*   **Wild (0.8 - 1.5)**: The AI becomes more unpredictable, creative, and intense. Good for high-energy scenes or brainstorming.

### Model Categories
When selecting a model, you will see tags:
*   **🛡️ (Safe - Restricted)**: These models are trained to be helpful and harmless. They may refuse certain NSFW or violent topics.
*   **🔓 (Unrestricted - Creative)**: These models (like Dolphin) are "uncensored." They will roleplay *anything* you ask, including violence, grimdark themes, or adult content.

---

## ✏️ Creating a Fantasy Card

A "Fantasy Card" defines the universe and characters for your chat.

### Example 1: High Fantasy Adventure
**Title**: The Lost Kingdom of Eldoria  
**Your Name**: Sir Kaelen (Knight)  
**AI Name**: Dungeon Master  
**Description**: A classic D&D style adventure.  
**System Prompt**:
```text
You are the Dungeon Master. I am Sir Kaelen, a knight seeking the lost crown. 
Describe the world in vivid detail. 
Manage NPCs, monsters, and loot. 
Do not act for me. Let me make my own choices.
When describing actions that happen in the world, use [brackets] for narration.
```

### Example 2: Sci-Fi Noir
**Title**: Neon Rain  
**Your Name**: Detective Vance  
**AI Name**: The City  
**Description**: A gritty cyberpunk mystery.  
**System Prompt**:
```text
You are the narrator of a dark cyberpunk city called Neo-Veridia. 
The year is 2099. Rain never stops. 
Describe the smells, the neon lights, and the tech. 
I am Vance, a private eye. 
Keep the tone cynical and dark.
Use [brackets] for scene descriptions and environmental details.
```

### Example 3: Character Roleplay
**Title**: Dinner with Dracula  
**Your Name**: Mina  
**AI Name**: Count Dracula  
**Description**: A tense conversation with a vampire.  
**System Prompt**:
```text
Roleplay as Count Dracula. You are polite, charming, but secretly dangerous. 
You are hosting me (Mina) for dinner at your castle. 
Speak in an old-fashioned, elegant manner. 
Do not reveal your vampire nature immediately.
Use [brackets] for your actions and mannerisms.
```

---

## 📝 Special Chat Formatting

### Bracket Notation for Narrative Text
Use **square brackets `[ ]`** in your messages to create italicized narrative text. This makes actions and descriptions stand out!

**Examples:**

**User Input:**
```
I slowly push open the creaking door. [The hinges groan in protest, echoing through the empty corridor.]
```

**Displays as:**
```
I slowly push open the creaking door. [The hinges groan in protest, echoing through the empty corridor.]
                                      ↑ This part appears in italic gray
```

**More Examples:**

Combat:
```
I draw my sword! [The blade gleams in the moonlight, ready for battle.]
```

Dialogue with Action:
```
"We need to leave. Now." [I grab your arm and start running toward the exit.]
```

Scene Setting:
```
[The tavern is packed tonight. Smoke fills the air, and the smell of ale is overwhelming.]
```

**Pro Tip**: The AI will often use brackets in its responses too! This helps distinguish between speech, actions, and narration.

---

## 🎯 Recommended LLM Models

### 🛡️ Censored/Safe Models (Good for Creative Writing)

**High VRAM (12GB+) - Desktop AMD/Nvidia/Intel**
- **Mistral-7B-Instruct-v0.3** (Q8) - Excellent for coherent storytelling, follows instructions well
- **Llama-3.1-8B-Instruct** (Q8) - Great dialogue, strong characterization
- **Nous-Hermes-2-Mistral-7B** (Q8) - Creative but balanced, good for fantasy/sci-fi

**Mid VRAM (8GB) - Desktop AMD/Nvidia/Intel**
- **Mistral-7B-Instruct-v0.2** (Q5_K_M) - Solid all-rounder, efficient
- **Llama-3.1-8B-Instruct** (Q4_K_M) - Good quality at lower VRAM
- **Phi-3-Medium-4K** (Q5_K_M) - Surprisingly creative for its size

**Low VRAM (4-6GB) - Laptop Dedicated GPU's or APU Systems AMD/Nvidia/Intel**
- **Llama-3.2-3B-Instruct** (Q5_K_M) - Small but capable, great for laptops
- **Phi-3-Mini-4K** (Q5_K_M) - Fast, efficient, good for quick responses
- **TinyLlama-1.1B-Chat** (Q8) - Ultra-low VRAM, surprisingly coherent

### 🔓 Unrestricted/Uncensored Models (Vivid & Unlocked)

**High VRAM (12GB+) - Desktop AMD/Nvidia/Intel**
- **Dolphin-2.9.2-Llama-3.1-8B** (Q8) - Best uncensored model, excellent creativity
- **WizardLM-2-8x22B** (Q4_K_M) - Massive context, very creative (needs 16GB+)
- **Nous-Capybara-34B** (Q4_K_M) - Extremely creative, no filters (needs 20GB+)

**Mid VRAM (8GB) - Desktop AMD/Nvidia/Intel**
- **Dolphin-2.9-Mistral-7B** (Q5_K_M) - Solid uncensored baseline
- **WizardLM-Uncensored-13B** (Q4_K_M) - Good balance of creativity and coherence
- **Samantha-Mistral-7B** (Q5_K_M) - Character-focused, emotionally expressive

**Low VRAM (4-6GB) - Laptop Dedicated GPU's or APU Systems AMD/Nvidia/Intel**
- **Dolphin-Phi-2.7B** (Q8) - Uncensored small model, laptop-friendly
- **OpenHermes-2.5-Mistral-7B** (Q3_K_M) - Compressed but capable
- **TinyDolphin-2.8-1.1B** (Q8) - Ultra-compact uncensored option

**Model Format Notes:**
- **Q8** = Highest quality, needs more VRAM
- **Q5_K_M** = Good balance of quality and size
- **Q4_K_M** = Smaller, fits in less VRAM
- **Q3_K_M** = Compressed, lowest quality but fastest

**Where to Download:**
- **Hugging Face**: https://huggingface.co/models (search for GGUF format)
- **TheBloke's Repository**: https://huggingface.co/TheBloke (pre-quantized models)
- **LM Studio**: Built-in model downloader with easy search

**Installation:**
1. Download `.gguf` model file
2. Place in your `models/` folder
3. Restart VOX-AI
4. Select from dropdown in Fantasy Editor

---

## ⚙️ Settings Guide

Click the **Settings** button in the sidebar to configure:

### Archive Settings
- **Archive Path**: Where to save old conversations (e.g., `D:/AI_Fantasy_Archives`)
- **Max Archive Size**: Total storage limit before cleanup (default: 100MB)

### Context Settings
- **Context Window Size**: How much the AI remembers at once
  - 2048 tokens = ~1,500 words (laptops)
  - 4096 tokens = ~3,000 words (standard)
  - 8192 tokens = ~6,000 words (high-end)

### RAG Memory System
- **Enable RAG**: Turn on/off automatic memory retrieval
- **Retrieve Count**: How many old messages to find (1-20)
  - 3-5 = Fast, focused memory
  - 10-15 = Comprehensive recall
  - 20 = Maximum context (slower)

### Understanding RAG
When RAG is enabled:
1. You mention something from 200 messages ago
2. RAG searches all archived conversations
3. Finds the 5 most relevant messages
4. Injects them into current context
5. AI responds with full historical knowledge

**Example:**
```
[100 messages ago - Archived]
You: "I swore an oath to protect the village from darkness."

[Current message]
You: "What was my oath about?"
AI: "You swore to protect the village from darkness, brave hero."
```

---

## 🎨 Themes

Customize the visual style of your chat:
*   **Default (Parchment)**: Classic paper feel, warm tones
*   **Dark (Night)**: Dark blue/purple for late-night sessions
*   **Blood**: Red/black for horror or intense combat
*   **Forest**: Deep greens for nature adventures
*   **Mystic**: Purple hues for magical, mysterious quests

Change themes in the Fantasy Editor and they apply immediately!

---

## 🛠️ Troubleshooting

**"The AI isn't replying!"**
*   Check the console window (the black box that opened with the app).
*   It might be loading the model (this takes time for the first message).
*   If it crashes, try a lower "Passion Level" or a smaller model.
*   Check your VRAM usage - you might need a smaller quantization (Q4 instead of Q8).

**"The response is cut off."**
*   Just type "Continue" and hit send.
*   Or increase `max_tokens` in your model config.

**"I want to reset the story."**
*   Click the **Reset** button (circular arrow) in the top right of the chat header. 
*   This wipes the current conversation memory but keeps your Fantasy Card.

**"RAG isn't finding old messages."**
*   Make sure RAG is enabled in Settings
*   Increase "Retrieve Count" to 10-15
*   The AI needs to archive messages first (happens at 80% context capacity)
*   Try using more specific keywords when referencing old events

**"Settings modal doesn't open."**
*   Make sure you've updated `app.js` with the settings code
*   Check browser console (F12) for JavaScript errors
*   Refresh the page (Ctrl+F5)

**"Context overflow errors."**
*   Increase Context Window Size in Settings
*   Enable RAG to auto-archive old messages
*   Use a model with larger context support

**"Out of VRAM errors."**
*   Use a smaller model quantization (Q4 instead of Q8)
*   Reduce `n_gpu_layers` in your model config
*   Close other GPU-intensive programs
*   Consider a smaller model (7B instead of 13B)

---

## 📊 Performance Tips

### For Best Speed:
- Use Q4 or Q5 quantizations
- Lower context window (2048-4096)
- Reduce RAG retrieve count (3-5)
- Pick models optimized for your hardware

### For Best Quality:
- Use Q8 quantizations
- Higher context window (8192)
- More RAG retrieval (10-15)
- Larger models if VRAM allows

### For Laptops:
- Models under 7B parameters
- Q4_K_M quantization
- Context window 2048-4096
- RAG enabled to compensate for smaller context
- Close background apps while running

---

## 📁 File Structure

```
VOX-AI/
├── app.py                  # Flask backend
├── vox_api.py              # LLM engine with RAG
├── Start_Fantasy.bat       # Windows launcher
├── global_settings.json    # Your settings (auto-created)
├── models/                 # Put .gguf models here
├── fantasies/              # Your fantasy cards (JSON)
├── context_archive/        # Archived conversations (auto-created)
├── templates/
│   └── index.html          # Main UI
└── static/
    ├── app.js              # Frontend JavaScript
    └── style.css           # Themes and styling
```

---

## 🎮 Advanced Tips

### Chain Multiple Cards
Create connected Fantasy Cards that share a universe:
- Card 1: "The Kingdom - Overview"
- Card 2: "The Dark Forest - Exploration"
- Card 3: "The Castle - Final Battle"

### Use Temperature Creatively
- **0.3-0.5**: Serious lore, consistent worldbuilding
- **0.7-0.9**: Balanced roleplay, good for most scenes
- **1.0-1.3**: High-energy combat, wild brainstorming
- **1.4-1.5**: Experimental, chaotic, surreal experiences

### Prompt Engineering
Add these to your System Prompt for better results:

**For Detailed Descriptions:**
```
Describe everything using all five senses. Use vivid adjectives.
```

**For Consistent Characters:**
```
Remember: Sir Aldric is brave but haunted by his past. He limps from an old wound.
Maintain this characterization in all responses.
```

**For Pacing Control:**
```
Let me control the pacing. Only describe immediate events. 
Wait for my input before advancing time or location.
```

---

## 🌟 Community & Support

**Found a Bug?** Open an issue on GitHub  
**Want to Contribute?** Pull requests welcome  
**Need Help?** Check the Discussions tab

---

## 📜 License

MIT License - Use freely, modify as needed, share with friends!

---

*Created for the VOX-AI Project*  
*Powered by llama.cpp and your imagination* 🚀
