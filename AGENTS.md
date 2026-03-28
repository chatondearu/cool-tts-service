# TTS Server Project - AGENTS.md

---

## 🎯 **Project Goal**
Deploy a **CPU-first**, **lightweight**, **customizable** TTS server (French voices only) in a Docker container, exposed through a simple API. Integrate with **Home Assistant** and **OpenClaw** for voice interactions.

---

## 📌 **Technical Specifications**

### 1️⃣ **Constraints**
- **CPU-only**: Tuned for Raspberry Pi (ARM64) or more powerful machines (x86_64).
- **Custom voices**: 2–3 preset French voices; add more via audio samples.
- **REST API**: Single endpoint to generate TTS from text and a voice id.
- **Docker**: Small image, easy to deploy and update.
- **Languages**: French only (to keep model size down).

---

## 2️⃣ **TTS Model Choice**

### **Comparison: Qwen 3 TTS vs Mistral AI Voxtral TTS**

| Criterion              | Qwen 3 TTS (1.7B)                          | Mistral AI Voxtral TTS (4B)               |
|------------------------|--------------------------------------------|--------------------------------------------|
| **Audio quality**      | ⭐⭐⭐⭐ (WER ~1.2–2.8%)                     | ⭐⭐⭐⭐⭐ (On par with ElevenLabs v3)       |
| **Latency (CPU)**      | ❌ Slow (RTF 3–5x)                         | ✅ Fast (RTF 6–9.7x, TTFA ~90ms)           |
| **Custom voices**      | ✅ Yes (~3s sample enough)                 | ✅ Yes (2–5s sample enough)                |
| **Multilingual**       | ✅ 10 languages (incl. French)             | ✅ 9 languages (incl. French)             |
| **Model size**         | ~3.4 GB (1.7B params)                      | ~8 GB (4B) or ~6 GB (Voxtral Mini)        |
| **CPU optimization**   | ❌ No (GPU recommended)                    | ✅ Yes (edge-oriented)                     |
| **Open source**        | ✅ Apache 2.0                              | ✅ Open weights                            |
| **Streaming**          | ✅ Yes (~100ms latency)                    | ✅ Yes (~90ms latency)                     |
| **Voice cloning**      | ✅ Yes (cross-lingual)                     | ✅ Yes (cross-lingual)                     |

---

### **Recommendation**
**👉 Mistral AI Voxtral TTS (Voxtral Mini 3B)** is the best fit for this use case:
- **CPU-oriented**: Light and fast, including on Raspberry Pi.
- **Strong audio quality**: Comparable to ElevenLabs v3.
- **Easy custom voices**: 2–5s samples are enough.
- **Very low latency**: Suited to real-time use (Home Assistant, OpenClaw).

*Alternative*: If RAM is tight (< 4 GB), **Qwen 3 TTS (0.6B)** is an option, but quality and latency will be worse.

---

## 3️⃣ **Project Architecture**

### **Technical stack**
- **Model**: `Voxtral Mini 3B` (or `Voxtral 4B` if you have headroom) — loaded via **`vllm_omni.OmniModel`** (`vllm-omni` package, Mistral’s recommended path for Voxtral), not a hand-rolled Transformers call in app code.
- **Framework**: [FastAPI](https://fastapi.tiangolo.com/) plus HF/torch deps (see `app/requirements.txt`).
- **Docker**: Image based on `python:3.11-slim` (`curl`, `ffmpeg`, `libsndfile1`); voices and cache mounted at `/app/voices` and `/app/cache`.
- **API**: `POST /tts` (`text`, `voice`), `GET /health`, `GET /voices`.
- **Voices**: `*.wav` files under `{VOICES_DIR}/default/` (ids = filename without extension); custom convention under `app/voices/custom/`.
- **Operator docs (English)**: [doc/README.md](doc/README.md) — technical source of truth aligned with the code.

---

### **Repository layout**
```
cool-tts-service/
├── flake.nix                   # Nix dev shell (Python 3.11 + system libs; see doc/deployment.md)
├── flake.lock
├── .envrc                      # Optional direnv: use flake
├── docker-compose.yml
├── Dockerfile
├── doc/                        # Technical docs (English), index: doc/README.md
├── docs/DEPLOYMENT.md          # Points to doc/deployment.md
├── app/
│   ├── main.py
│   ├── model.py
│   ├── voices/
│   │   ├── default/            # *.wav → ids listed by GET /voices
│   │   └── custom/             # Custom samples (convention)
│   └── requirements.txt
├── scripts/
│   ├── add_voice.py
│   └── test_tts.py
├── AGENTS.md
└── README.md
```

---

## 4️⃣ **Deployment Steps**

### **1️⃣ Prerequisites**
- **Docker** and **Docker Compose** installed.
- **At least 4 GB RAM** (8 GB recommended for Voxtral 4B).
- **CPU**: ARM64 (Raspberry Pi) or x86_64.

---

### **2️⃣ Configuration**
#### **docker-compose.yml**
```yaml
version: '3.8'

services:
  cool-tts-service:
    build: .
    container_name: cool-tts-service
    ports:
      - "8000:8000"
    volumes:
      - ./app/voices:/app/voices
      - ./app/cache:/app/cache
    environment:
      - MODEL_NAME=mistralai/Voxtral-Mini-3B-TTS-2603  # or Voxtral-4B-TTS-2603
      - VOICES_DIR=/app/voices
      - CACHE_DIR=/app/cache
      - LOG_LEVEL=info
    restart: unless-stopped
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 4G  # 8G for Voxtral 4B
```

---

#### **Dockerfile** (summary)
```dockerfile
FROM python:3.11-slim
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl git ffmpeg libsndfile1 && rm -rf /var/lib/apt/lists/*
COPY app/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app/ .
RUN mkdir -p /app/voices/default /app/voices/custom /app/cache
EXPOSE 8000
HEALTHCHECK CMD curl -f http://localhost:8000/health || exit 1
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
```

---

#### **requirements.txt** (excerpt)
```
fastapi==0.110.0
uvicorn==0.29.0
loguru==0.7.2
vllm-omni==0.1.0
transformers==4.40.0
torch==2.2.0
soundfile==0.12.1
librosa==0.10.1
huggingface-hub==0.22.0
```

---

### **3️⃣ Deploy**
```bash
# Clone the repo (or create the layout manually)
git clone <project_url> cool-tts-service
cd cool-tts-service

# Build and start the container
docker-compose up -d --build
```

---

### **4️⃣ Add a custom voice**
```bash
# Put a 2–5s audio sample somewhere, then:
python scripts/add_voice.py --name "my_voice" --sample app/voices/custom/sample.wav
```

---

### **5️⃣ Test the API**
```bash
curl -X POST "http://localhost:8000/tts" \
  -H "Content-Type: application/json" \
  -d '{"text": "Bonjour, ceci est un test de synthèse vocale.", "voice": "generate_0_FR"}' \
  --output output.wav
```

---

## 5️⃣ **Home Assistant & OpenClaw integration**

### **1️⃣ Home Assistant**
- Use the **RESTful Command** integration to call the TTS API.
- Example configuration:
  ```yaml
  rest_command:
    tts_speak:
      url: "http://<SERVER_IP>:8000/tts"
      method: POST
      payload: '{"text": "{{ text }}", "voice": "{{ voice }}"}'
      content_type: "application/json"
  ```
- Trigger TTS from a **script** or **automation**.

---

### **2️⃣ OpenClaw**
- Use the `tts` tool to send requests to the TTS server.
- Example:
  ```python
  tts(text="Hello from OpenClaw!", channel="telegram")
  ```
- Set the TTS server URL in `openclaw.json`:
  ```json
  {
    "tts": {
      "serverUrl": "http://<SERVER_IP>:8000/tts"
    }
  }
  ```

---

## 6️⃣ **Maintenance & roadmap**

### **1️⃣ Updates**
- **Model**: Watch for new Voxtral TTS releases on [Hugging Face](https://huggingface.co/mistralai).
- **Docker**: Rebuild with `docker-compose up -d --build`.

---

### **2️⃣ Possible enhancements**
- **Response cache**: Store frequent TTS outputs to cut latency.
- **Streaming**: Smoother interactive playback.
- **Web UI**: Manage custom voices and try TTS in the browser.
- **Whisper integration**: Full STT + TTS loop.

---

## 7️⃣ **Resources**
- [Voxtral TTS documentation](https://docs.mistral.ai/capabilities/audio/text_to_speech)
- [Hugging Face — Voxtral Mini 3B](https://huggingface.co/mistralai/Voxtral-Mini-3B-TTS-2603)
- [Hugging Face — Voxtral 4B](https://huggingface.co/mistralai/Voxtral-4B-TTS-2603)
- [FastAPI documentation](https://fastapi.tiangolo.com/)
- [Docker Compose documentation](https://docs.docker.com/compose/)

---

## 8️⃣ **Repository status (TODO)**
- [x] Project layout and Docker.
- [x] API (`main.py`) and model loader (`model.py`, `OmniModel`).
- [x] Environment variables: `MODEL_NAME`, `CACHE_DIR` → `HF_HOME`, `LOG_LEVEL`, `VOICES_DIR`.
- [x] Scripts `scripts/add_voice.py` and `scripts/test_tts.py`.
- [x] Technical docs under `doc/` (+ HA / OpenClaw integration here and in the README).
- [ ] Validate ARM64 / Raspberry Pi (`torch` / `vllm-omni` wheels per hardware).
- [ ] Additional default French voices (`app/voices/default/*.wav`) if product needs them.
- [ ] Performance benchmarks (latency, RAM) and targeted optimizations.
