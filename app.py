import os
import json
import uuid
import glob
from flask import Flask, render_template, request, jsonify, Response, stream_with_context
from vox_api import VoxAPI

app = Flask(__name__)
engine = None  # Lazy load the engine

FANTASIES_DIR = "fantasies"
MODELS_DIR = "models"

# Ensure directories exist
os.makedirs(FANTASIES_DIR, exist_ok=True)
os.makedirs(MODELS_DIR, exist_ok=True)

def get_engine():
    global engine
    if engine is None:
        # Initial boot - we can defer model loading until a card is selected if we want,
        # but for now let's just init the wrapper. Real loading happens when we pick a fantasy (maybe).
        # Actually vox_api auto-loads on init. Let's make it more flexible.
        # For this MVP, we might just re-init engine when switching models.
        try:
            engine = VoxAPI(verbose=True)
        except Exception as e:
            print(f"Error initializing engine: {e}")
    return engine

@app.route('/')
def home():
    return render_template('index.html')

# --- Fantasy Management API ---

@app.route('/api/fantasies', methods=['GET'])
def list_fantasies():
    fantasies = []
    for filepath in glob.glob(os.path.join(FANTASIES_DIR, "*.json")):
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
                fantasies.append(data)
        except Exception as e:
            print(f"Error reading {filepath}: {e}")
    return jsonify(fantasies)

@app.route('/api/fantasies', methods=['POST'])
def save_fantasy():
    data = request.json
    if not data.get('id'):
        data['id'] = str(uuid.uuid4())
    
    filename = f"{data['id']}.json"
    filepath = os.path.join(FANTASIES_DIR, filename)
    
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4)
    
    return jsonify({"status": "success", "id": data['id']})

@app.route('/api/fantasies/<fantasy_id>', methods=['GET'])
def get_fantasy(fantasy_id):
    filepath = os.path.join(FANTASIES_DIR, f"{fantasy_id}.json")
    if not os.path.exists(filepath):
        return jsonify({"error": "Fantasy not found"}), 404
        
    with open(filepath, 'r', encoding='utf-8') as f:
        data = json.load(f)
    return jsonify(data)

@app.route('/api/fantasies/<fantasy_id>', methods=['DELETE'])
def delete_fantasy(fantasy_id):
    filepath = os.path.join(FANTASIES_DIR, f"{fantasy_id}.json")
    if os.path.exists(filepath):
        os.remove(filepath)
        return jsonify({"status": "deleted"})
    return jsonify({"error": "Not found"}), 404

# --- Chat API ---

@app.route('/api/chat', methods=['POST'])
def chat():
    global engine
    data = request.json
    user_message = data.get('message')
    history = data.get('history', []) # We might pass full history or let backend manage it, 
                                      # but for statelessness better to pass context or use engine's history if session based.
                                      # VoxAPI has internal history. We should probably clear it and sync it.
    
    system_prompt = data.get('system_prompt', "You are a helpful assistant.")
    model_config = data.get('model_config', {})

    # Check if we need to reload model (simplified logic: just check if engine is up)
    # In a full app, we'd check if current model matches requested model.
    # Check if we need to reload model
    requested_model = model_config.get('model', 'default')
    
    # If engine is not loaded, OR if model changed (and it's not default), reload
    # Note: VoxAPI.model_name stores the filename
    should_reload = False
    if engine is None:
        should_reload = True
    elif requested_model != 'default' and requested_model != engine.model_name:
        should_reload = True
        
    if should_reload:
        try:
            print(f"[VOX] Loading model: {requested_model}...")
            # Construct absolute path if specific model requested
            model_path = None
            if requested_model != 'default':
                model_path = os.path.abspath(os.path.join(MODELS_DIR, requested_model))
                
            engine = VoxAPI(model_path=model_path, verbose=True)
        except Exception as e:
            print(f"[ERROR] Failed to load model: {e}")
            return jsonify({"error": f"Failed to load model: {e}"}), 500

    # --- NAME INJECTION LOGIC ---
    # We prefix messages with names to force the model to respect roles.
    # e.g. "York: Hello" instead of just "Hello"
    user_name = data.get('user_name', 'User')
    ai_name = data.get('ai_name', 'AI')
    
    # 1. Modify System Prompt to enforce identity
    # We add "Write the next response." to encourage immediate action vs meta-explanation.
    identity_instruction = f"\n[System Note: Roleplay as {ai_name}. User is {user_name}. Use [brackets] for actions/narration. Write {ai_name}'s next response only. Do NOT repeat the user's dialogue.]"
    final_system_prompt = system_prompt + identity_instruction

    # 2. Modify History (Context)
    # We construct a temporary history for the engine that includes names
    context_history = [{"role": "system", "content": final_system_prompt}]
    
    if history:
        for msg in history:
            role_name = user_name if msg['role'] == 'user' else ai_name
            context_history.append({
                "role": msg['role'],
                "content": f"{role_name}: {msg['content']}"
            })

    # 3. Modify Current Message
    current_message_with_name = f"{user_name}: {user_message}"
    
    # Sync to engine (using our modified context)
    engine.history = context_history

    print(f"[VOX] Fantasy Request | {user_name} -> {ai_name} | Model: {model_config.get('model', 'Default')}")

    def generate():
        # Stream response
        # We assume the model might output "{ai_name}: " at the start.
        # We want to strip that so we don't duplicate the UI nameplate.
        
        prefix_to_strip = f"{ai_name}:"
        buffer = ""
        
        for token in engine.chat(current_message_with_name, stream=True):
            buffer += token
            
            # If we haven't printed anything yet, check if we are building the prefix
            if len(buffer) < len(prefix_to_strip) + 5: # Small buffer window
                if buffer.strip().startswith(prefix_to_strip):
                    # We found the prefix, remove it and print the rest
                    # But only remove it once at the start
                    clean_content = buffer.split(prefix_to_strip, 1)[-1].lstrip()
                    if clean_content:
                        # If there is content after the prefix, yield it
                        for char in clean_content:
                            yield char
                            print(char, end="", flush=True)
                        buffer = "" # Reset buffer, we are done filtering
                    continue
                elif len(buffer) > len(prefix_to_strip) and not buffer.strip().startswith(prefix_to_strip):
                     # Buffer is longer than prefix and doesn't match, so just flush it
                     for char in buffer:
                        yield char
                        print(char, end="", flush=True)
                     buffer = ""
            else:
                # Buffer is huge or we are past start, just flush whatever is there
                if buffer:
                    for char in buffer:
                        yield char
                        print(char, end="", flush=True)
                    buffer = ""
        
        # Flush any remaining buffer if we ended exactly on a partial match (rare)
        if buffer:
             clean_content = buffer.replace(prefix_to_strip, "").lstrip()
             for char in clean_content:
                yield char
                print(char, end="", flush=True)

        print("\n[VOX] Request complete.")

    return Response(stream_with_context(generate()), mimetype='text/plain')

@app.route('/api/reset', methods=['POST'])
def reset_chat():
    if engine:
        engine.clear_history()
    return jsonify({"status": "cleared"})

@app.route('/api/models', methods=['GET'])
def list_models():
    # List .gguf files
    if not os.path.exists(MODELS_DIR):
        return jsonify([])
    files = [f for f in os.listdir(MODELS_DIR) if f.endswith(".gguf")]
    return jsonify(files)

if __name__ == '__main__':
    print("VOX-AI Web Client Starting...")
    # Open browser automatically (only once)
    import webbrowser
    if not os.environ.get("WERKZEUG_RUN_MAIN"):
        webbrowser.open("http://127.0.0.1:5000")
    app.run(host='127.0.0.1', port=5000, debug=True)
