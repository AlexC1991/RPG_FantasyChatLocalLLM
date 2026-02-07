import os
import json
import uuid
import glob
from flask import Flask, render_template, request, jsonify, Response, stream_with_context
from vox_api import VoxAPI

app = Flask(__name__)
engine = None

FANTASIES_DIR = "fantasies"
MODELS_DIR = "models"
SETTINGS_FILE = "global_settings.json"

os.makedirs(FANTASIES_DIR, exist_ok=True)
os.makedirs(MODELS_DIR, exist_ok=True)

DEFAULT_SETTINGS = {
    "archive_path": "./context_archive",
    "max_archive_size_mb": 100,
    "context_window_size": 4096,
    "enable_rag": True,
    "rag_retrieve_count": 5
}

def load_settings():
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, 'r') as f:
                settings = json.load(f)
                merged = DEFAULT_SETTINGS.copy()
                merged.update(settings)
                return merged
        except:
            pass
    return DEFAULT_SETTINGS.copy()

def save_settings(settings):
    with open(SETTINGS_FILE, 'w') as f:
        json.dump(settings, f, indent=4)

def get_engine():
    global engine
    if engine is None:
        settings = load_settings()
        try:
            engine = VoxAPI(
                verbose=True,
                n_ctx=settings.get('context_window_size', 4096),
                archive_path=settings.get('archive_path', './context_archive'),
                max_archive_size_mb=settings.get('max_archive_size_mb', 100),
                enable_rag=settings.get('enable_rag', True),
                rag_retrieve_count=settings.get('rag_retrieve_count', 5)
            )
        except Exception as e:
            print(f"Error initializing engine: {e}")
    return engine

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/api/settings', methods=['GET'])
def get_settings():
    return jsonify(load_settings())

@app.route('/api/settings', methods=['POST'])
def update_settings():
    global engine
    new_settings = request.json
    
    if 'archive_path' in new_settings:
        os.makedirs(new_settings['archive_path'], exist_ok=True)
    
    if 'max_archive_size_mb' in new_settings:
        new_settings['max_archive_size_mb'] = max(1, int(new_settings['max_archive_size_mb']))
    
    if 'context_window_size' in new_settings:
        new_settings['context_window_size'] = max(512, int(new_settings['context_window_size']))
    
    if 'rag_retrieve_count' in new_settings:
        new_settings['rag_retrieve_count'] = max(1, min(20, int(new_settings['rag_retrieve_count'])))
    
    save_settings(new_settings)
    
    if engine:
        engine = None
    
    return jsonify({"status": "success", "settings": new_settings})

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

@app.route('/api/chat', methods=['POST'])
def chat():
    global engine
    data = request.json
    user_message = data.get('message')
    history = data.get('history', [])
    system_prompt = data.get('system_prompt', "You are a helpful assistant.")
    model_config = data.get('model_config', {})
    fantasy_id = data.get('fantasy_id', None)

    requested_model = model_config.get('model', 'default')
    
    should_reload = False
    if engine is None:
        should_reload = True
    elif requested_model != 'default' and requested_model != engine.model_name:
        should_reload = True
        
    if should_reload:
        try:
            print(f"[VOX] Loading model: {requested_model}...")
            settings = load_settings()
            
            model_path = None
            if requested_model != 'default':
                model_path = os.path.abspath(os.path.join(MODELS_DIR, requested_model))
                
            engine = VoxAPI(
                model_path=model_path,
                verbose=True,
                n_ctx=settings.get('context_window_size', 4096),
                archive_path=settings.get('archive_path', './context_archive'),
                max_archive_size_mb=settings.get('max_archive_size_mb', 100),
                enable_rag=settings.get('enable_rag', True),
                rag_retrieve_count=settings.get('rag_retrieve_count', 5)
            )
        except Exception as e:
            print(f"[ERROR] Failed to load model: {e}")
            return jsonify({"error": f"Failed to load model: {e}"}), 500

    if fantasy_id:
        engine.set_fantasy_context(fantasy_id)

    user_name = data.get('user_name', 'User')
    ai_name = data.get('ai_name', 'AI')
    
    identity_instruction = f"\n[System Note: Roleplay as {ai_name}. User is {user_name}. Use [brackets] for actions/narration. Write {ai_name}'s next response only. Do NOT repeat the user's dialogue.]"
    final_system_prompt = system_prompt + identity_instruction

    context_history = [{"role": "system", "content": final_system_prompt}]
    
    if history:
        for msg in history:
            role_name = user_name if msg['role'] == 'user' else ai_name
            context_history.append({
                "role": msg['role'],
                "content": f"{role_name}: {msg['content']}"
            })

    current_message_with_name = f"{user_name}: {user_message}"
    engine.history = context_history

    print(f"[VOX] Fantasy Request | {user_name} -> {ai_name} | Model: {model_config.get('model', 'Default')}")

    def generate():
        prefix_to_strip = f"{ai_name}:"
        buffer = ""
        
        for token in engine.chat(current_message_with_name, stream=True):
            buffer += token
            
            if len(buffer) < len(prefix_to_strip) + 5:
                if buffer.strip().startswith(prefix_to_strip):
                    clean_content = buffer.split(prefix_to_strip, 1)[-1].lstrip()
                    if clean_content:
                        for char in clean_content:
                            yield char
                            print(char, end="", flush=True)
                        buffer = ""
                    continue
                elif len(buffer) > len(prefix_to_strip) and not buffer.strip().startswith(prefix_to_strip):
                     for char in buffer:
                        yield char
                        print(char, end="", flush=True)
                     buffer = ""
            else:
                if buffer:
                    for char in buffer:
                        yield char
                        print(char, end="", flush=True)
                    buffer = ""
        
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
    if not os.path.exists(MODELS_DIR):
        return jsonify([])
    files = [f for f in os.listdir(MODELS_DIR) if f.endswith(".gguf")]
    return jsonify(files)

@app.route('/api/stats', methods=['GET'])
def get_stats():
    if engine:
        return jsonify(engine.get_stats())
    return jsonify({"error": "Engine not initialized"}), 503

if __name__ == '__main__':
    print("VOX-AI Web Client Starting...")
    print("Features: Context Archiving + RAG Retrieval")
    import webbrowser
    if not os.environ.get("WERKZEUG_RUN_MAIN"):
        webbrowser.open("http://127.0.0.1:5000")
    app.run(host='127.0.0.1', port=5000, debug=True)
