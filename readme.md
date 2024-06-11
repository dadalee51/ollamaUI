**edit ollama service params
sudo systemctl edit ollama.service

[Service]
Environment="OLLAMA_HOST=0.0.0.0"
Environment="OLLAMA_ORIGINS=*"

**restart ollama 
sudo systemctl restart ollama

** ps aux | grep ollama 
kill that ps id to shutdown ollama
