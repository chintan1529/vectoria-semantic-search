"use client";

import { useState, useEffect } from "react";

export type SystemStatus = "online" | "degraded" | "offline";

export function useSystemStatus() {
  const [status, setStatus] = useState<SystemStatus>("online");

  useEffect(() => {
    // In Phase 0-3, we'll simulate this.
    // Later in Phase 4 when the API is built, this will poll the backend /health endpoint.
    const checkStatus = async () => {
      try {
        // Placeholder for future API call
        // const res = await fetch("/api/health");
        // if (res.ok) setStatus("online");
        // else setStatus("degraded");
        
        // For now, always online
        setStatus("online");
      } catch (error) {
        setStatus("offline");
      }
    };

    checkStatus();
    
    // Poll every 30 seconds
    const interval = setInterval(checkStatus, 30000);
    return () => clearInterval(interval);
  }, []);

  return status;
}
