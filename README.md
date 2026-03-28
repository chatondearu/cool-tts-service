# TTS Server

A lightweight, CPU-first TTS server using **Mistral AI's Voxtral TTS** (Mini 3B) with FastAPI and Docker.

**Documentation:** [doc/README.md](doc/README.md) (full technical docs in English).

## 🚀 Features
- **CPU-optimized** TTS (works on Raspberry Pi or x86_64).
- **French voices** (default + customizable).
- **FastAPI** for easy integration (Home Assistant, OpenClaw, etc.).
- **Dockerized** for simple deployment.

---

## 📦 Setup
### 1. Clone the Project
```bash
git clone <your-repo-url> TTS_Project
cd TTS_Project
```

### 2. Build and Run
```bash
docker-compose up -d --build
```

### 3. Test the API
```bash
curl -X POST "http://localhost:8000/tts" \
  -H "Content-Type: application/json" \
  -d '{"text": "Bonjour, ceci est un test.", "voice": "fr_female_1"}' \
  --output output.wav
```

---

## 🎤 Voices
### Default Voices
- `fr_female_1` (French female)
- *Add more in `app/voices/default/`.*

### Add a Custom Voice
1. Place a 3-5s `.wav` sample anywhere, then run from the repo root:  
   `python scripts/add_voice.py --name my_voice --sample path/to/sample.wav`  
   (defaults to `app/voices/custom/`).
2. Or copy manually to `app/voices/custom/` and use the stem as `voice` in the API.

---

## 🔧 Configuration
| Environment Variable | Description                     | Default                          |
|----------------------|---------------------------------|----------------------------------|
| `MODEL_NAME`         | TTS model                       | `mistralai/Voxtral-Mini-3B-TTS-2603` |
| `VOICES_DIR`         | Path to voices                  | `/app/voices`                     |
| `CACHE_DIR`          | Hugging Face cache (`HF_HOME`)  | _(unset; use `/app/cache` in Docker)_ |
| `LOG_LEVEL`          | Logging level                   | `INFO`                            |

---

## 📡 API Endpoints
| Endpoint       | Method | Description                     | Example Payload                          |
|---------------|--------|---------------------------------|------------------------------------------|
| `/tts`        | POST   | Generate speech                 | `{"text": "Hello", "voice": "fr_female_1"}` |
| `/health`     | GET    | Health check                    | -                                        |
| `/voices`     | GET    | List available voices           | -                                        |

---

## 🐳 Docker
### Build
```bash
docker-compose build
```

### Run
```bash
docker-compose up -d
```

### Logs
```bash
docker-compose logs -f
```

---

## 🛠 Development
### Install Dependencies
```bash
pip install -r app/requirements.txt
```

### Run Locally
From the repository root (so `app` resolves correctly):

```bash
uvicorn app.main:app --reload --app-dir .
```

Quick API check:

```bash
python scripts/test_tts.py --base-url http://127.0.0.1:8000
```

---

## 📄 License
MIT