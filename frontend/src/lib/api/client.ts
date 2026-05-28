import { RAGResponse, ErrorReason } from "./types";

// ==========================================
// MOCK DATA GENERATOR (For Development Phase)
// ==========================================

const MOCK_RESPONSE: RAGResponse = {
  answer: "Neural networks learn through a process called backpropagation [Doc 1], where the network adjusts its weights based on the error between predicted and actual outputs. This is often optimized using algorithms like Adam or SGD. The learning rate controls the step size during this weight update phase [Doc 2]. In modern architectures like transformers, self-attention mechanisms allow the model to weight the importance of different parts of the input sequence differently [Doc 3].",
  citations: {
    "Doc 1": {
      rank: 1,
      score: 0.892,
      chunk: {
        chunk_id: "chk_1",
        doc_id: "doc_ai_1",
        text: "Backpropagation is a method used in artificial neural networks to calculate a gradient that is needed in the calculation of the weights to be used in the network. It is commonly used to train deep neural networks.",
        metadata: { doc_id: "doc_ai_1", source: "wikipedia", title: "Artificial Neural Network", category: "ai" },
        chunk_index: 3,
        word_count: 38
      }
    },
    "Doc 2": {
      rank: 2,
      score: 0.841,
      chunk: {
        chunk_id: "chk_2",
        doc_id: "doc_ai_2",
        text: "The learning rate is a hyperparameter that controls how much to change the model in response to the estimated error each time the model weights are updated. Choosing the learning rate is challenging as a value too small may result in a long training process.",
        metadata: { doc_id: "doc_ai_2", source: "textbook", title: "Deep Learning Fundamentals", category: "ai" },
        chunk_index: 12,
        word_count: 45
      }
    },
    "Doc 3": {
      rank: 3,
      score: 0.795,
      chunk: {
        chunk_id: "chk_3",
        doc_id: "doc_ai_3",
        text: "Self-attention, sometimes called intra-attention, is an attention mechanism relating different positions of a single sequence in order to compute a representation of the sequence. It has been successfully used in machine reading, abstractive summarization, or image description generation.",
        metadata: { doc_id: "doc_ai_3", source: "paper", title: "Attention Is All You Need", category: "ai" },
        chunk_index: 0,
        word_count: 39
      }
    }
  },
  retrieved_results: [
    {
      rank: 1,
      score: 0.892,
      chunk: {
        chunk_id: "chk_1",
        doc_id: "doc_ai_1",
        text: "Backpropagation is a method used in artificial neural networks to calculate a gradient that is needed in the calculation of the weights to be used in the network. It is commonly used to train deep neural networks.",
        metadata: { doc_id: "doc_ai_1", source: "wikipedia", title: "Artificial Neural Network", category: "ai" },
        chunk_index: 3,
        word_count: 38
      }
    },
    {
      rank: 2,
      score: 0.841,
      chunk: {
        chunk_id: "chk_2",
        doc_id: "doc_ai_2",
        text: "The learning rate is a hyperparameter that controls how much to change the model in response to the estimated error each time the model weights are updated. Choosing the learning rate is challenging as a value too small may result in a long training process.",
        metadata: { doc_id: "doc_ai_2", source: "textbook", title: "Deep Learning Fundamentals", category: "ai" },
        chunk_index: 12,
        word_count: 45
      }
    },
    {
      rank: 3,
      score: 0.795,
      chunk: {
        chunk_id: "chk_3",
        doc_id: "doc_ai_3",
        text: "Self-attention, sometimes called intra-attention, is an attention mechanism relating different positions of a single sequence in order to compute a representation of the sequence. It has been successfully used in machine reading, abstractive summarization, or image description generation.",
        metadata: { doc_id: "doc_ai_3", source: "paper", title: "Attention Is All You Need", category: "ai" },
        chunk_index: 0,
        word_count: 39
      }
    },
    {
      rank: 4,
      score: 0.652,
      chunk: {
        chunk_id: "chk_4",
        doc_id: "doc_ai_4",
        text: "Convolutional neural networks are regularized versions of multilayer perceptrons. Multilayer perceptrons usually mean fully connected networks, that is, each neuron in one layer is connected to all neurons in the next layer. The 'fully-connectedness' of these networks makes them prone to overfitting data.",
        metadata: { doc_id: "doc_ai_4", source: "wikipedia", title: "Convolutional Neural Network", category: "ai" },
        chunk_index: 1,
        word_count: 42
      }
    }
  ],
  context_stats: {
    num_chunks: 4,
    total_characters: 850,
    average_score: 0.795,
    unique_sources: 4
  },
  latency_ms: 1250,
  model_name: "gemini-2.5-pro",
  refused: false,
  refusal_reason: null,
  generation_meta: {
    model_used: "gemini-2.5-pro",
    generation_latency_ms: 850,
    prompt_tokens: 1240,
    completion_tokens: 312,
    total_tokens: 1552,
    finish_reason: "stop",
    prompt_version: "v1.2",
    retrieved_chunk_ids: ["chk_1", "chk_2", "chk_3", "chk_4"],
    citation_count: 3
  },
  num_retrieved: 4
};

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
        const res = await fetch(`${this.baseUrl}/ready`);
        return res.ok;
     } catch (e) {
        return false;
     }
  }
}

// Export singleton instance with mock mode DISABLED for production/live usage
export const api = new VectoriaAPIClient();
