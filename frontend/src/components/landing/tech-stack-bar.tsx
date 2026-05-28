export function TechStackBar() {
  return (
    <div className="mt-16 flex items-center justify-center gap-3 text-xs font-mono text-zinc-600 uppercase tracking-wider">
      <span>all-MiniLM-L6-v2</span>
      <span className="text-zinc-800">·</span>
      <span>384-dim</span>
      <span className="text-zinc-800">·</span>
      <span>FAISS IndexFlatIP</span>
      <span className="text-zinc-800">·</span>
      <span>3,592 chunks</span>
      <span className="text-zinc-800">·</span>
      <span>Cross-Encoder Reranking</span>
    </div>
  );
}
