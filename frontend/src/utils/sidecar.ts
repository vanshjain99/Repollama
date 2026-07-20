import { Command } from '@tauri-apps/api/shell';

export async function spawnSidecar(): Promise<void> {
  try {
    const command = Command.sidecar('bin/repollama-engine');
    const child = await command.spawn();
    console.log('[Sidecar] Spawned repollama-engine process, PID:', child.pid);
  } catch (err) {
    console.warn('[Sidecar] Could not spawn sidecar process (it may already be running or running outside Tauri environment):', err);
  }
}

export async function ping_server(endpoint = 'http://localhost:8000/health'): Promise<boolean> {
  try {
    const response = await fetch(endpoint, { method: 'GET' });
    if (response.ok) {
      const data = await response.json();
      return data.status === 'healthy' || response.status === 200;
    }
    return false;
  } catch {
    return false;
  }
}

export async function waitForServer(
  maxRetries = 30,
  intervalMs = 1000,
  onAttempt?: (attempt: number) => void
): Promise<boolean> {
  for (let i = 1; i <= maxRetries; i++) {
    if (onAttempt) onAttempt(i);
    const healthy = await ping_server();
    if (healthy) return true;
    await new Promise((resolve) => setTimeout(resolve, intervalMs));
  }
  return false;
}
