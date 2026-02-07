import sys
import os
import psutil
import ctypes
import time
from llama_cpp import Llama

# ==========================================
# 0. SYSTEM PREP
# ==========================================
try:
    p = psutil.Process(os.getpid())
    p.nice(psutil.HIGH_PRIORITY_CLASS)
except: pass

root_path = os.path.abspath(".")
os.environ["PATH"] += os.pathsep + root_path
if hasattr(os, 'add_dll_directory'): os.add_dll_directory(root_path)

# ==========================================
# 1. CALL THE HANDSHAKE
# ==========================================
print("[VOX CORE] Initializing...")
print("[VOX CORE] Requesting Hardware Handshake...")

try:
    import machine_engine_handshake
    # This call will trigger the [HANDSHAKE] prints
    detected_mode, phys_cores, cfg = machine_engine_handshake.get_hardware_config()
    print("[VOX CORE] Handshake received. Locking in configuration.")

except ImportError:
    sys.exit("\n[CRITICAL] Missing 'machine_engine_handshake.py'. Cannot detect hardware.")


# Apply Config
os.environ["GGML_VK_FORCE_BUSY_WAIT"] = cfg["busy_wait"]
os.environ["GGML_NUMA"] = "0"
os.environ["GGML_BACKEND_SEARCH_PATH"] = root_path
os.environ["LLAMA_CPP_LIB"] = os.path.join(root_path, "llama.dll")

# Load Backend
try:
    ggml = ctypes.CDLL(os.path.join(root_path, "ggml.dll"))
    if hasattr(ggml, 'ggml_backend_load_all'): ggml.ggml_backend_load_all()
except: pass

# ==========================================
# 2. MODEL SELECTOR
# ==========================================
MODELS_DIR = "./models"
model_files = [f for f in os.listdir(MODELS_DIR) if f.endswith(".gguf")]

print("\n============================================")
print(f" VOX-AI UNIVERSAL ENGINE | STATUS: ONLINE")
print("============================================")
print(f" [VOX CORE] Mode:   {detected_mode}")
print(f" [VOX CORE] Config: {cfg['n_gpu_layers']} Layers | {cfg['n_threads']} Threads")
print("============================================")

for idx, model_name in enumerate(model_files):
    print(f" [{idx + 1}] {model_name}")

while True:
    try:
        choice = int(input("\nSelect a model: "))
        if 1 <= choice <= len(model_files):
            selected_model = model_files[choice - 1]
            break
    except ValueError: pass

# ==========================================
# 3. INITIALIZATION
# ==========================================
print(f"\n[VOX CORE] Booting Llama.cpp with {detected_mode} profile...")

try:
    llm = Llama(
        model_path=os.path.join(MODELS_DIR, selected_model),
        n_ctx=2048,
        
        # INJECTING CONFIG FROM HANDSHAKE
        n_gpu_layers=cfg['n_gpu_layers'],
        n_threads=cfg['n_threads'],
        n_threads_batch=cfg['n_threads_batch'],
        n_batch=cfg['n_batch'],
        flash_attn=cfg['flash_attn'],
        use_mlock=cfg['use_mlock'],
        cache_type_k=cfg['cache_type_k'],
        cache_type_v=cfg['cache_type_v'],
        
        use_mmap=True,
        verbose=True
    )

    print("[VOX CORE] Engine Loaded. Performing Warmup...")
    llm.create_chat_completion(messages=[{"role": "user", "content": "ready"}], max_tokens=1)
    print("[VOX CORE] Warmup Complete. Listening for input.")
    
except Exception as e:
    sys.exit(f"\n[CRITICAL] {e}")

# ==========================================
# 4. CHAT LOOP
# ==========================================
print("\n" + "="*40)
print(" VOX-AI READY")
print("="*40)
history = [{"role": "system", "content": "You are a helpful assistant."}]

while True:
    user_in = input("USER: ")
    if user_in.lower() in ["exit", "quit"]: break
    history.append({"role": "user", "content": user_in})
    print("VOX: ", end="", flush=True)
    
    token_count = 0
    start_time = time.time()
    full_resp = ""
    
    try:
        stream = llm.create_chat_completion(
            messages=history, stream=True, max_tokens=2000,
            temperature=0.7,
            repeat_penalty=1.1,
            top_k=40
        )
        
        first_token = True
        for chunk in stream:
            if "content" in chunk["choices"][0]["delta"]:
                if first_token: first_token = False
                
                tok = chunk["choices"][0]["delta"]["content"]
                print(tok, end="", flush=True)
                full_resp += tok
                token_count += 1
                
        total_time = time.time() - start_time
        tps = token_count / total_time if total_time > 0 else 0
        
        print(f"\n\n[STATS] {token_count} tokens in {total_time:.2f}s | Speed: {tps:.2f} t/s")
        print("-" * 40)
        
        history.append({"role": "assistant", "content": full_resp})
        
    except KeyboardInterrupt:
        print("\n[Interrupted]")
        break