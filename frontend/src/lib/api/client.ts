import { RAGResponse, ErrorReason } from "./types";

// ==========================================
// API CLIENT
// ==========================================

export class VectoriaAPIClient {
  private baseUrl: string;

  constructor(baseUrl?: string) {
    this.baseUrl = baseUrl || process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
  }

  async query(queryText: string, topK: number = 5, retries = 1): Promise<RAGResponse> {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 60000); // 60s max timeout

    try {
      const response = await fetch(`${this.baseUrl}/api/query`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query: queryText, top_k: topK, stream: false }),
        signal: controller.signal
      });

      clearTimeout(timeoutId);

      if (!response.ok) {
        if (response.status === 503) {
           throw new Error("System is initializing. Please try again in a few seconds.");
        }
        
        // Parse structured error if possible
        let errorMsg = `API Error: ${response.status}`;
        try {
          const errBody = await response.json();
          if (errBody && errBody.detail) errorMsg = errBody.detail;
        } catch (e) {
          // ignore parsing error
        }
        throw new Error(errorMsg);
      }

      const data: RAGResponse = await response.json();
      return data;
    } catch (error: any) {
      clearTimeout(timeoutId);
      
      if (error.name === 'AbortError') {
         throw new Error("Request timed out. The backend took too long to respond.");
      }

      // Retry logic for transient failures
      if (retries > 0) {
        console.warn(`Query failed, retrying... (${retries} attempts left)`);
        await new Promise(resolve => setTimeout(resolve, 2000));
        return this.query(queryText, topK, retries - 1);
      }

      console.error("Query failed permanently:", error);
      
      // Handle connection refused / backend offline
      if (error instanceof TypeError && error.message === "Failed to fetch") {
         throw new Error("Backend is offline or still warming up. Please wait a moment and try again.");
      }
      
      throw error;
    }
  }
  
  async checkHealth(): Promise<boolean> {
     try {
        const res = await fetch(`${this.baseUrl}/api/ready`);
        return res.ok;
     } catch (e) {
        return false;
     }
  }

  // --- Analytics Methods ---
  
  async getPlatformStatus() {
    try {
      const response = await fetch(`${this.baseUrl}/api/analytics/platform-status`);
      if (!response.ok) return null;
      return await response.json();
    } catch (e) {
      return null;
    }
  }

  async getEvalDashboard() {
    try {
      const response = await fetch(`${this.baseUrl}/api/analytics/eval-dashboard`);
      if (!response.ok) return null;
      return await response.json();
    } catch (e) {
      return null;
    }
  }

  async getQueryIntelligence() {
    try {
      const response = await fetch(`${this.baseUrl}/api/analytics/queries`);
      if (!response.ok) return null;
      return await response.json();
    } catch (e) {
      return null;
    }
  }

  async getProviderAnalytics() {
    try {
      const response = await fetch(`${this.baseUrl}/api/analytics/providers`);
      if (!response.ok) return null;
      return await response.json();
    } catch (e) {
      return null;
    }
  }
}

// Export singleton instance with mock mode DISABLED for production/live usage
export const api = new VectoriaAPIClient();
