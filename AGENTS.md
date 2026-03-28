# TTS Server Project - AGENTS.md

---

## 🎯 **Objectif du Projet**
Déployer un serveur TTS **CPU-first**, **léger**, et **customisable** (voix françaises uniquement) dans un conteneur Docker, accessible via une API simple. Intégration avec **Home Assistant** et **OpenClaw** pour des interactions vocales.

---

## 📌 **Spécifications Techniques**

### 1️⃣ **Contraintes**
- **CPU-only** : Optimisé pour Raspberry Pi (ARM64) ou machines plus puissantes (x86_64).
- **Voix custom** : 2-3 voix françaises préconfigurées, possibilité d’en ajouter via des échantillons audio.
- **API REST** : Endpoint unique pour générer du TTS à partir d’un texte et d’une voix.
- **Docker** : Image légère, facile à déployer et à mettre à jour.
- **Multilingue** : Français uniquement (pour limiter la taille du modèle).

---

## 2️⃣ **Choix du Modèle TTS**

### **Comparatif : Qwen 3 TTS vs Mistral AI Voxtral TTS**

| Critère                | Qwen 3 TTS (1.7B)                          | Mistral AI Voxtral TTS (4B)               |
|------------------------|--------------------------------------------|--------------------------------------------|
| **Qualité audio**      | ⭐⭐⭐⭐ (WER ~1.2-2.8%)                     | ⭐⭐⭐⭐⭐ (Parité avec ElevenLabs v3)       |
| **Latence (CPU)**      | ❌ Lente (RTF 3-5x)                         | ✅ Rapide (RTF 6-9.7x, TTFA ~90ms)         |
| **Voix custom**        | ✅ Oui (3s de sample suffisent)             | ✅ Oui (2-5s de sample suffisent)          |
| **Multilingue**        | ✅ 10 langues (dont français)              | ✅ 9 langues (dont français)               |
| **Taille du modèle**   | ~3.4 Go (1.7B params)                      | ~8 Go (4B params) ou ~6 Go (Voxtral Mini) |
| **Optimisation CPU**   | ❌ Non (GPU recommandé)                     | ✅ Oui (optimisé pour edge devices)        |
| **Open Source**        | ✅ Apache 2.0                               | ✅ Open weights                            |
| **Streaming**          | ✅ Oui (latence ~100ms)                     | ✅ Oui (latence ~90ms)                     |
| **Clonage vocal**      | ✅ Oui (cross-lingual)                      | ✅ Oui (cross-lingual)                     |

---

### **Recommandation**
**👉 Mistral AI Voxtral TTS (Voxtral Mini 3B)** est le meilleur choix pour ton usage :
- **Optimisé pour le CPU** : Léger et rapide, même sur Raspberry Pi.
- **Qualité audio supérieure** : Parité avec ElevenLabs v3.
- **Voix custom faciles à ajouter** : 2-5s de sample suffisent.
- **Latence ultra-faible** : Idéal pour des interactions en temps réel (Home Assistant, OpenClaw).

*Alternative* : Si la RAM est limitée (< 4 Go), **Qwen 3 TTS (0.6B)** peut être envisagé, mais la qualité audio et la latence seront moins bonnes.

---

## 3️⃣ **Architecture du Projet**

### **Stack Technique**
- **Modèle** : `Voxtral Mini 3B` (ou `Voxtral 4B` si ressources suffisantes) — chargé via **`vllm_omni.OmniModel`** (paquet `vllm-omni`, recommandé par Mistral pour Voxtral), pas un appel Transformers manuel dans le code applicatif.
- **Framework** : [FastAPI](https://fastapi.tiangolo.com/) + dépendances HF/torch (voir `app/requirements.txt`).
- **Docker** : Image basée sur `python:3.11-slim` (`curl`, `ffmpeg`, `libsndfile1`); voix et cache montés sous `/app/voices` et `/app/cache`.
- **API** : `POST /tts` (`text`, `voice`), `GET /health`, `GET /voices`.
- **Voix** : fichiers `*.wav` sous `{VOICES_DIR}/default/` (ids = nom sans extension); voix custom sous `app/voices/custom/` (convention).
- **Documentation opérateur (anglais)** : [doc/README.md](doc/README.md) — source de vérité technique alignée sur le code.

---

### **Structure des Fichiers**
```
cool-tts-service/
├── docker-compose.yml
├── Dockerfile
├── doc/                        # Doc technique (anglais), index : doc/README.md
├── docs/DEPLOYMENT.md          # Renvoi vers doc/deployment.md
├── app/
│   ├── main.py
│   ├── model.py
│   ├── voices/
│   │   ├── default/            # *.wav → ids listés par GET /voices
│   │   └── custom/             # Échantillons custom (convention)
│   └── requirements.txt
├── scripts/
│   ├── add_voice.py
│   └── test_tts.py
├── AGENTS.md
└── README.md
```

---

## 4️⃣ **Étapes de Déploiement**

### **1️⃣ Prérequis**
- Machine avec **Docker** et **Docker Compose** installés.
- **4 Go de RAM minimum** (8 Go recommandés pour Voxtral 4B).
- **CPU** : ARM64 (Raspberry Pi) ou x86_64.

---

### **2️⃣ Configuration**
#### **docker-compose.yml**
```yaml
version: '3.8'

services:
  tts-server:
    build: .
    container_name: tts-server
    ports:
      - "8000:8000"
    volumes:
      - ./app/voices:/app/voices
      - ./app/cache:/app/cache
    environment:
      - MODEL_NAME=mistralai/Voxtral-Mini-3B-TTS-2603  # ou Voxtral-4B-TTS-2603
      - VOICES_DIR=/app/voices
      - CACHE_DIR=/app/cache
      - LOG_LEVEL=info
    restart: unless-stopped
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 4G  # 8G pour Voxtral 4B
```

---

#### **Dockerfile** (résumé)
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

#### **requirements.txt** (extraits)
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

### **3️⃣ Déploiement**
```bash
# Cloner le projet (ou créer la structure manuellement)
git clone <url_du_projet> TTS_Project
cd TTS_Project

# Construire et lancer le conteneur
docker-compose up -d --build
```

---

### **4️⃣ Ajouter une Voix Custom**
```bash
# Placer un échantillon audio (2-5s) dans app/voices/custom/
python scripts/add_voice.py --name "ma_voix" --sample app/voices/custom/sample.wav
```

---

### **5️⃣ Tester l'API**
```bash
curl -X POST "http://localhost:8000/tts" \
  -H "Content-Type: application/json" \
  -d '{"text": "Bonjour, ceci est un test de synthèse vocale.", "voice": "fr_female_1"}' \
  --output output.wav
```

---

## 5️⃣ **Intégration avec Home Assistant & OpenClaw**

### **1️⃣ Home Assistant**
- Utiliser l’intégration **RESTful Command** pour appeler l’API TTS.
- Exemple de configuration :
  ```yaml
  rest_command:
    tts_speak:
      url: "http://<IP_DU_SERVEUR>:8000/tts"
      method: POST
      payload: '{"text": "{{ text }}", "voice": "{{ voice }}"}'
      content_type: "application/json"
  ```
- Utiliser un **script** ou une **automation** pour déclencher le TTS.

---

### **2️⃣ OpenClaw**
- Utiliser le tool `tts` pour envoyer des requêtes au serveur TTS.
- Exemple :
  ```python
  tts(text="Bonjour Chaton !", channel="telegram")
  ```
- Configurer l’URL du serveur TTS dans `openclaw.json` :
  ```json
  {
    "tts": {
      "serverUrl": "http://<IP_DU_SERVEUR>:8000/tts"
    }
  }
  ```

---

## 6️⃣ **Maintenance & Évolutions**

### **1️⃣ Mises à Jour**
- **Modèle** : Surveiller les nouvelles versions de Voxtral TTS sur [Hugging Face](https://huggingface.co/mistralai).
- **Docker** : Reconstruire l’image avec `docker-compose up -d --build`.

---

### **2️⃣ Évolutions Possibles**
- **Ajouter un cache** : Stocker les générations TTS fréquentes pour réduire la latence.
- **Support du streaming** : Pour des interactions encore plus fluides.
- **Interface web** : Pour gérer les voix custom et tester le TTS.
- **Intégration avec Whisper** : Pour un système complet STT + TTS.

---

## 7️⃣ **Ressources**
- [Documentation Voxtral TTS](https://docs.mistral.ai/capabilities/audio/text_to_speech)
- [Hugging Face - Voxtral Mini 3B](https://huggingface.co/mistralai/Voxtral-Mini-3B-TTS-2603)
- [Hugging Face - Voxtral 4B](https://huggingface.co/mistralai/Voxtral-4B-TTS-2603)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Docker Compose Documentation](https://docs.docker.com/compose/)

---

## 8️⃣ **État du dépôt (TODO)**
- [x] Structure du projet et Docker.
- [x] API (`main.py`) et chargeur modèle (`model.py`, `OmniModel`).
- [x] Variables d’environnement : `MODEL_NAME`, `CACHE_DIR` → `HF_HOME`, `LOG_LEVEL`, `VOICES_DIR`.
- [x] Scripts `scripts/add_voice.py` et `scripts/test_tts.py`.
- [x] Documentation technique sous `doc/` (+ intégration HA / OpenClaw décrite ici et dans le README).
- [ ] Valider ARM64 / Raspberry Pi (wheels `torch` / `vllm-omni` selon matériel).
- [ ] Secondes voix françaises par défaut (`app/voices/default/*.wav`) si besoin produit.
- [ ] Mesures de perf (latence, RAM) et optimisations ciblées.