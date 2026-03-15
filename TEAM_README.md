# Anima Studio - Presentation Guide 🚀

This project generates professional math and physics animations using AI and Manim. This guide is for teammates who **do not have a GPU/VRAM** or **Ollama installed**.

## 🌟 How to Run (Cloud/No-GPU Mode)

If you don't have Ollama or a dedicated GPU, you should use **Google Gemini** as the AI engine. It is free, fast, and runs in the cloud.

### 1. Get a Gemini API Key
1. Go to [Google AI Studio](https://aistudio.google.com/app/apikey).
2. Click **Create API Key**.
3. Copy the key.

### 2. Configure the Project
Open the `.env` file in the root directory and change these lines:

```env
# 1. Switch provider to gemini
LLM_PROVIDER=gemini

# 2. Paste your Gemini API Key
GEMINI_API_KEY=your_key_here

# 3. Model settings
LLM_MODEL=gemini-2.0-flash-exp
LLM_TEMPERATURE=0.2
```

### 3. Launch the Project
Make sure you have [Docker Desktop](https://www.docker.com/products/docker-desktop/) installed and running.

1. Open a terminal in this folder.
2. Run:
   ```bash
   docker-compose up -d --build
   ```
3. Open your browser to: **http://localhost:3000**

---

## 🛠 Troubleshooting for Low-End PCs

- **Rendering is slow**: Since you don't have a GPU, the Manim renderer will use your CPU. Complex animations might take 2-5 minutes.
- **Docker is heavy**: If your PC is struggling, close other apps (Chrome, etc.) while the animation is rendering.
- **Memory Errors**: If Docker crashes, go to *Docker Desktop Settings -> Resources* and increase the RAM limit to at least 4GB.

## 📝 Best Prompts to Show Mam
Try these prompts for a high-quality demo:
- *"Explain matrix multiplication of two 2x2 matrices with step-by-step highlights."*
- *"Visualize a ball moving in a projectile motion parabolic curve."*
- *"Show how a derivative represents the slope of a tangent line on a curve."*
