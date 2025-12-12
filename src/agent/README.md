## Plan
- Build a local-first coding agent using **AWS Strands**.
- Support multiple LLM backends behind one interface:
  - Bedrock (paid, managed)
  - Ollama local (Docker on laptop)
  - Ollama remote (EC2 GPU via SSM port-forward to localhost)
- Should also support SAFELY running "head;ess agents" in github workflow runners or codebuild or something

## Stuff
- `agent/`: CLI entrypoints and orchestration
- `agent/llm_backends/`:
  - backend selection (bedrock vs ollama)
  - configuration and connection handling
- `agent/tools/`:
  - tool definitions exposed to the agent (repo inspection, file I/O, etc.)

## Runtime model
- The agent process runs on your machine.
- If using remote Ollama, you establish an SSM tunnel so the backend still looks like `http://localhost:11434`.
- Tools are defined client-side and handed to Strands at agent initialization.