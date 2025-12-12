## Plan
- Provide one-command workflows for:
  - starting the GPU instance **via Lambda** (with forced auto-stop timer)
  - stopping it early when you're done
  - opening an SSM shell session
  - creating an SSM port-forward tunnel to the remote Ollama port

## Intended scripts
- `gpu_start.sh`: invokes `StartGpuInstance` Lambda (must include duration)
- `gpu_stop.sh`: invokes `StopGpuInstance` Lambda
- `ssm_shell.sh`: starts an interactive SSM session to the instance
- `ssm_tunnel_ollama.sh`: port-forwards remote `11434` to local `11434`
- `run_agent.sh`: runs the local Strands agent with the chosen backend config

## Principle
No script should require opening inbound ports or directly calling EC2 start/stop from your human credentials.