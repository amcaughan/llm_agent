## Plan
- Provide a minimal Docker setup for running **Ollama locally** on a weak laptop.
- Keep it simple: one container, persistent model storage via a Docker volume.
- Use a small model for early testing (tool-calling behavior + agent plumbing), then swap to EC2 GPU later.