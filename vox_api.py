import os
import time
import json
import numpy as np
from datetime import datetime
from typing import Generator, Dict, List, Optional, Union
from pathlib import Path
from llama_cpp import Llama
import machine_engine_handshake

class VoxAPI:
    """
    A clean API wrapper for the VOX-AI Engine.
    Features: Smart context management with disk archiving and RAG retrieval.
    """
    
    def __init__(self, model_path: str = None, verbose: bool = False, n_ctx: int = 4096,
                 archive_path: str = None, max_archive_size_mb: int = 100,
                 enable_rag: bool = False, rag_retrieve_count: int = 3):
        """
        Initialize the VOX Engine.
        """
        self.verbose = verbose
        self.history: List[Dict[str, str]] = []
        self.n_ctx = n_ctx
        self.max_tokens_per_response = 2048
        
        # Archive settings
        self.archive_path = archive_path or "./context_archive"
        self.max_archive_size_bytes = max_archive_size_mb * 1024 * 1024
        self.current_fantasy_id = None
        
        # RAG settings
        self.enable_rag = enable_rag
        self.rag_retrieve_count = rag_retrieve_count
        self.embedding_cache = {}
        
        # Create archive directory
        Path(self.archive_path).mkdir(parents=True, exist_ok=True)
        self.context_reserve = 512
        self.total_archived_messages = 0
        self.total_rag_retrievals = 0
        
        # 1. Hardware Handshake
        self.mode, self.phys_cores, self.config = machine_engine_handshake.get_hardware_config()
        if self.verbose:
            print(f"[VOX API] RAG Enabled: {self.enable_rag}")
            
        # 2. Env Optimizations
        self._apply_env_optimizations()
        
        # 3. Model Loading
        if model_path is None:
            model_path = self._auto_find_model()
        
        self.model_name = os.path.basename(model_path)
        
        # 4. Initialize Llama
        # CRITICAL FIX: We strictly enforce embedding=False unless RAG is on.
        use_embedding = True if self.enable_rag else False

        self.llm = Llama(
            model_path=model_path,
            n_ctx=self.n_ctx,
            embedding=use_embedding,  # <--- THIS IS THE FIX
            
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
        self.warmup()

    def _apply_env_optimizations(self):
        import ctypes
        root_path = os.path.abspath(".")
        if "busy_wait" in self.config:
            os.environ["GGML_VK_FORCE_BUSY_WAIT"] = self.config["busy_wait"]
        
        local_dll = os.path.join(root_path, "llama.dll")
        if os.path.exists(local_dll):
            if hasattr(os, 'add_dll_directory'): 
                try: os.add_dll_directory(root_path)
                except: pass
            os.environ["GGML_NUMA"] = "0"
            os.environ["GGML_BACKEND_SEARCH_PATH"] = root_path
            os.environ["LLAMA_CPP_LIB"] = local_dll
            
            try:
                ggml_path = os.path.join(root_path, "ggml.dll")
                if os.path.exists(ggml_path):
                    ggml = ctypes.CDLL(ggml_path)
                    if hasattr(ggml, 'ggml_backend_load_all'):
                        ggml.ggml_backend_load_all()
            except: pass

    def _auto_find_model(self) -> str:
        models_dir = os.path.abspath("./models")
        files = [f for f in os.listdir(models_dir) if f.endswith(".gguf")]
        if not files: raise FileNotFoundError("No models found")
        return os.path.join(models_dir, files[0])

    def _estimate_tokens(self, text: str) -> int:
        return len(text) // 4

    def _get_embedding(self, text: str) -> np.ndarray:
        if not self.enable_rag: return np.zeros(4096)
        if text in self.embedding_cache: return self.embedding_cache[text]
        try:
            embedding = self.llm.create_embedding(text)['data'][0]['embedding']
            embedding_array = np.array(embedding)
            norm = np.linalg.norm(embedding_array)
            if norm > 0: embedding_array = embedding_array / norm
            self.embedding_cache[text] = embedding_array
            return embedding_array
        except: return np.zeros(4096)

    def _cosine_similarity(self, vec1: np.ndarray, vec2: np.ndarray) -> float:
        return np.dot(vec1, vec2)

    def _load_archives_for_fantasy(self) -> List[Dict]:
        if not self.current_fantasy_id: return []
        fantasy_folder = Path(self.archive_path) / self.current_fantasy_id
        if not fantasy_folder.exists(): return []
        
        all_messages = []
        files = sorted(fantasy_folder.glob("archive_*.json"))
        # OPTIMIZATION: Only read last 3 files
        for archive_file in files[-3:]:
            try:
                with open(archive_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    all_messages.extend(data.get('messages', []))
            except: pass
        return all_messages

    def _retrieve_relevant_context(self, query: str) -> List[Dict[str, str]]:
        if not self.enable_rag: return []
        # Optimization: Skip short queries
        if len(query) < 10: return []
        
        archived = self._load_archives_for_fantasy()
        if not archived: return []
        
        query_embedding = self._get_embedding(query)
        scored = []
        for msg in archived:
            if msg.get('role') == 'system': continue
            content = msg.get('content', '')
            if not content: continue
            
            similarity = self._cosine_similarity(query_embedding, self._get_embedding(content))
            scored.append({'message': msg, 'similarity': similarity})
            
        scored.sort(key=lambda x: x['similarity'], reverse=True)
        top = scored[:self.rag_retrieve_count]
        self.total_rag_retrievals += len(top)
        return [item['message'] for item in top]

    def _inject_rag_context(self, messages: List[Dict]) -> str:
        if not messages: return ""
        parts = ["[Retrieved Context:]"]
        for msg in messages:
            parts.append(f"- {msg['role']}: {msg['content'][:200]}")
        parts.append("[End Context]\n")
        return "\n".join(parts)

    def _archive_messages(self, messages: List[Dict]):
        if not messages: return
        # Folder logic
        folder = Path(self.archive_path)
        if self.current_fantasy_id: folder = folder / self.current_fantasy_id
        folder.mkdir(parents=True, exist_ok=True)
        
        # Save
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        with open(folder / f"archive_{timestamp}.json", 'w', encoding='utf-8') as f:
            json.dump({"messages": messages, "timestamp": timestamp}, f)
            
        self.total_archived_messages += len(messages)
        if self.enable_rag:
            for msg in messages: 
                if msg.get('role') != 'system': self._get_embedding(msg.get('content', ''))

    def set_fantasy_context(self, fantasy_id: str):
        self.current_fantasy_id = fantasy_id

    def _trim_history_with_archive(self):
        if not self.history: return
        # Calculate usage
        usage = sum(self._estimate_tokens(m['content']) + 50 for m in self.history)
        limit = self.n_ctx - self.max_tokens_per_response - self.context_reserve
        
        if usage < limit * 0.8: return
        
        # Archive oldest 25%
        sys_msg = self.history[0] if self.history[0]['role'] == 'system' else None
        msgs = self.history[1:] if sys_msg else self.history
        
        cut = max(1, len(msgs) // 4)
        self._archive_messages(msgs[:cut])
        
        new_hist = []
        if sys_msg: new_hist.append(sys_msg)
        new_hist.extend(msgs[cut:])
        self.history = new_hist

    def warmup(self):
        try: self.llm.create_chat_completion(messages=[{"role":"user","content":"."}], max_tokens=1)
        except: pass

    def chat(self, user_message: str, stream: bool = True, system_prompt: str = None, temperature: float = 0.8):
        # RAG Injection
        rag_context = []
        if self.enable_rag and self.current_fantasy_id:
            rag_context = self._retrieve_relevant_context(user_message)
            
        # History Init
        if not self.history:
            base_sys = system_prompt or "You are a helpful assistant."
            if rag_context:
                base_sys = self._inject_rag_context(rag_context) + "\n" + base_sys
            self.history.append({"role": "system", "content": base_sys})
        else:
            # Update RAG in existing system prompt
            if rag_context and self.history[0]['role'] == 'system':
                curr = self.history[0]['content']
                if "[Retrieved Context:]" in curr:
                    curr = curr.split("[End Context]\n")[-1]
                self.history[0]['content'] = self._inject_rag_context(rag_context) + "\n" + curr

        self.history.append({"role": "user", "content": user_message})
        self._trim_history_with_archive()
        
        if stream: return self._stream_response(temperature)
        return self._full_response(temperature)

    def _stream_response(self, temperature):
        full = ""
        try:
            stream = self.llm.create_chat_completion(
                messages=self.history, max_tokens=self.max_tokens_per_response,
                temperature=temperature, top_k=40, repeat_penalty=1.1, stream=True
            )
            for chunk in stream:
                if "content" in chunk["choices"][0]["delta"]:
                    tok = chunk["choices"][0]["delta"]["content"]
                    full += tok
                    yield tok
        except ValueError: pass # Simple failover
        self.history.append({"role": "assistant", "content": full})

    def _full_response(self, temperature):
        resp = self.llm.create_chat_completion(
            messages=self.history, max_tokens=self.max_tokens_per_response,
            temperature=temperature, top_k=40, repeat_penalty=1.1, stream=False
        )
        text = resp["choices"][0]["message"]["content"]
        self.history.append({"role": "assistant", "content": text})
        return text

    def clear_history(self):
        self.history = []
        self.embedding_cache.clear()

    def get_stats(self):
        return {
            "model": self.model_name,
            "messages": len(self.history),
            "rag_enabled": self.enable_rag
        }

    def close(self):
        """
        Explicitly release resources to prevent VRAM leaks.
        """
        if hasattr(self, 'llm') and self.llm:
            del self.llm
            self.llm = None
        self.embedding_cache.clear()
        self.history = []