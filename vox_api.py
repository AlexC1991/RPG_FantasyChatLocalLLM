import os
import time
from typing import Generator, Dict, List, Optional, Union
from llama_cpp import Llama
import machine_engine_handshake

class VoxAPI:
    """
    A clean API wrapper for the VOX-AI Engine.
    Designed for easy integration into chat software.
    """
    
    def __init__(self, model_path: str = None, verbose: bool = False):
        """
        Initialize the VOX Engine with automatic hardware optimization.
        
        Args:
            model_path: Path to the .gguf model file. If None, auto-detects from ./models
            verbose: Enable detailed logging
        """
        self.verbose = verbose
        self.history: List[Dict[str, str]] = []
        
        # 1. Hardware Handshake
        self.mode, self.phys_cores, self.config = machine_engine_handshake.get_hardware_config()
        if self.verbose:
            print(f"[VOX API] Mode: {self.mode}")
            print(f"[VOX API] Config: {self.config}")
            
        # 2. Apply Environment Optimizations
        self._apply_env_optimizations()
        
        # 3. Model Loading
        if model_path is None:
            model_path = self._auto_find_model()
            
        if not os.path.exists(model_path):
            raise FileNotFoundError(f"Model not found at: {model_path}")
            
        self.model_name = os.path.basename(model_path)
        
        # 4. Initialize Llama
        self.llm = Llama(
            model_path=model_path,
            n_ctx=2048, # Standard context window
            
            # Hardware Config
            n_gpu_layers=self.config['n_gpu_layers'],
            n_threads=self.config['n_threads'],
            n_threads_batch=self.config['n_threads_batch'],
            n_batch=self.config['n_batch'],
            flash_attn=self.config['flash_attn'],
            use_mlock=self.config['use_mlock'],
            cache_type_k=self.config['cache_type_k'],
            cache_type_v=self.config['cache_type_v'],
            
            use_mmap=True,
            verbose=self.verbose
        )
        
        # 5. Warmup
        self.warmup()

    def _apply_env_optimizations(self):
        """Apply environment variables for APU performance and load Backend"""
        import ctypes
        root_path = os.path.abspath(".")
        
        # 1. Performance Variables
        if "busy_wait" in self.config:
            os.environ["GGML_VK_FORCE_BUSY_WAIT"] = self.config["busy_wait"]
        
        # 2. DLL Override (Game-Style Engine)
        # We MUST use the local DLLs because they contain the specific Vulkan backend
        # that the pip package might be missing or conflicting with.
        local_dll = os.path.join(root_path, "llama.dll")
        
        if os.path.exists(local_dll):
            if hasattr(os, 'add_dll_directory'): 
                try: os.add_dll_directory(root_path)
                except: pass
            
            os.environ["GGML_NUMA"] = "0"
            os.environ["GGML_BACKEND_SEARCH_PATH"] = root_path
            os.environ["LLAMA_CPP_LIB"] = local_dll
            
            # 3. Explicit Backend Loading (Crucial for Vulkan/GPU)
            try:
                # Based on vox_core_chat.py logic
                ggml_path = os.path.join(root_path, "ggml.dll")
                if os.path.exists(ggml_path):
                    ggml = ctypes.CDLL(ggml_path)
                    if hasattr(ggml, 'ggml_backend_load_all'):
                        ggml.ggml_backend_load_all()
                    if self.verbose:
                        print(f"[VOX API] Loaded backends from {ggml_path}")
            except Exception as e:
                print(f"[VOX API] Warning: Failed to load backends: {e}")
                
        else:
            if self.verbose:
                print("[VOX API] Using system/pip installed llama-cpp-python binaries.")

    def _auto_find_model(self) -> str:
        """Find the first .gguf file in ./models"""
        models_dir = os.path.abspath("./models")
        if not os.path.exists(models_dir):
            raise FileNotFoundError("Models directory './models' not found")
            
        files = [f for f in os.listdir(models_dir) if f.endswith(".gguf")]
        if not files:
            raise FileNotFoundError("No .gguf models found in ./models")
            
        return os.path.join(models_dir, files[0])

    def warmup(self):
        """Run a silent inference to load weights into RAM/VRAM"""
        if self.verbose: print("[VOX API] Warming up...")
        self.llm.create_chat_completion(
            messages=[{"role": "user", "content": "."}], 
            max_tokens=1
        )

    def chat(self, user_message: str, stream: bool = True, system_prompt: str = None) -> Union[str, Generator[str, None, None]]:
        """
        Send a message to the AI and get a response.
        
        Args:
            user_message: The text input from the user
            stream: If True, returns a generator yielding tokens. If False, returns full string.
            system_prompt: Optional override for system prompt (default is "You are a helpful assistant.")
        """
        
        # Initialize history if empty
        if not self.history:
            sys_msg = system_prompt or "You are a helpful assistant."
            self.history.append({"role": "system", "content": sys_msg})
            
        # Add user message
        self.history.append({"role": "user", "content": user_message})
        
        if stream:
            return self._stream_response()
        else:
            return self._full_response()

    def _stream_response(self) -> Generator[str, None, None]:
        """Internal generator for streaming responses"""
        full_response = ""
        
        stream = self.llm.create_chat_completion(
            messages=self.history,
            max_tokens=2048,
            temperature=0.7,
            top_k=40,
            repeat_penalty=1.1,
            stream=True
        )
        
        for chunk in stream:
            if "content" in chunk["choices"][0]["delta"]:
                token = chunk["choices"][0]["delta"]["content"]
                full_response += token
                yield token
                
        # Update history with the complete response
        self.history.append({"role": "assistant", "content": full_response})

    def _full_response(self) -> str:
        """Internal method for non-streaming response"""
        response = self.llm.create_chat_completion(
            messages=self.history,
            max_tokens=2048,
            temperature=0.7,
            top_k=40,
            repeat_penalty=1.1,
            stream=False
        )
        
        text = response["choices"][0]["message"]["content"]
        self.history.append({"role": "assistant", "content": text})
        return text

    def clear_history(self):
        """Reset conversation context"""
        self.history = []

    def get_stats(self):
        """Get info about the loaded model and hardware"""
        return {
            "model": self.model_name,
            "mode": self.mode,
            "cores": self.phys_cores,
            "gpu_layers": self.config['n_gpu_layers']
        }

# Usage Example
if __name__ == "__main__":
    print("Testing VOX API...")
    try:
        engine = VoxAPI(verbose=True)
        print(f"Loaded: {engine.model_name}")
        
        print("\nUser: Hello!")
        print("Bot: ", end="")
        for token in engine.chat("Hello!", stream=True):
            print(token, end="", flush=True)
        print("\n\nTest Complete.")
    except Exception as e:
        print(f"Error: {e}")
