import json
import math
import numpy as np
from typing import List, Dict, Any

class RetrievalMetrics:
    @staticmethod
    def calculate_dcg(relevances: List[int]) -> float:
        """Calculates Discounted Cumulative Gain."""
        dcg = 0.0
        for i, rel in enumerate(relevances):
            dcg += (2**rel - 1) / math.log2(i + 2)
        return dcg

    @staticmethod
    def calculate_ndcg(retrieved_relevances: List[int], expected_relevances: List[int]) -> float:
        """Calculates normalized Discounted Cumulative Gain."""
        dcg = RetrievalMetrics.calculate_dcg(retrieved_relevances)
        idcg = RetrievalMetrics.calculate_dcg(sorted(expected_relevances, reverse=True))
        if idcg == 0:
            return 0.0
        return dcg / idcg

    @staticmethod
    def evaluate_query(retrieved_chunk_ids: List[str], expected_sources: List[str], k_values=[5, 10]) -> Dict[str, float]:
        """Calculates Recall, Precision, MRR, nDCG at given K values."""
        metrics = {}
        expected_set = set(expected_sources)
        
        # Binary relevance for Precision/Recall
        relevances = [1 if cid in expected_set else 0 for cid in retrieved_chunk_ids]
        
        for k in k_values:
            rel_k = relevances[:k]
            retrieved_k = len(rel_k)
            
            # Recall
            hits = sum(rel_k)
            recall = hits / len(expected_set) if expected_set else 0.0
            metrics[f"recall@{k}"] = recall
            
            # Precision
            precision = hits / retrieved_k if retrieved_k > 0 else 0.0
            metrics[f"precision@{k}"] = precision
            
            # nDCG
            ndcg = RetrievalMetrics.calculate_ndcg(rel_k, [1] * len(expected_set))
            metrics[f"ndcg@{k}"] = ndcg
            
        # MRR
        mrr = 0.0
        for i, rel in enumerate(relevances):
            if rel == 1:
                mrr = 1.0 / (i + 1)
                break
        metrics["mrr"] = mrr
        
        return metrics

class AnswerMetrics:
    @staticmethod
    def extract_claims(answer: str) -> List[str]:
        # Simple split by sentence for claims.
        return [c.strip() for c in answer.split('.') if len(c.strip()) > 10]
        
    @staticmethod
    async def evaluate_faithfulness(primary_judge, answer: str, context_chunks: List[str], secondary_judge=None) -> Dict[str, Any]:
        """Uses Dual LLM-as-a-judge to determine if answer is supported by context."""
        context_str = "\n".join(context_chunks)
        prompt = f"""
        Context: {context_str}
        
        Answer: {answer}
        
        Is the Answer completely supported by the Context without external hallucinations?
        Reply with ONLY a number between 0.0 and 1.0 representing the faithfulness score.
        """
        primary_score = 0.5
        secondary_score = None
        
        try:
            res = await primary_judge.generate([{"role": "user", "content": prompt}], temperature=0.0)
            primary_score = float(res.text.strip())
            primary_score = min(max(primary_score, 0.0), 1.0)
        except Exception:
            primary_score = 0.5 # fallback

        if secondary_judge:
            try:
                res2 = await secondary_judge.generate([{"role": "user", "content": prompt}], temperature=0.0)
                secondary_score = float(res2.text.strip())
                secondary_score = min(max(secondary_score, 0.0), 1.0)
            except Exception as e:
                # Secondary judge unavailable (e.g. network failure)
                secondary_score = -1.0 # indicating failure to evaluate
        
        if secondary_score is not None and secondary_score >= 0.0:
            divergence = abs(primary_score - secondary_score)
            agreement = 1.0 - divergence
            final_score = (primary_score + secondary_score) / 2.0
            status = "DUAL_JUDGE_SUCCESS"
        else:
            final_score = primary_score
            divergence = 0.0
            agreement = 1.0
            status = "SECONDARY_UNAVAILABLE" if secondary_judge else "SINGLE_JUDGE"

        return {
            "faithfulness": final_score,
            "primary_score": primary_score,
            "secondary_score": secondary_score,
            "divergence": divergence,
            "agreement_rate": agreement,
            "status": status
        }

class CitationMetrics:
    @staticmethod
    async def verify_citations(primary_judge, claims: List[str], chunks: List[str], secondary_judge=None) -> Dict[str, Any]:
        """Verifies citations through Dual-Judge Verification."""
        verified = 0
        weak = 0
        unsupported = 0
        
        for claim in claims:
            best_chunk = None
            max_overlap = 0.0
            
            # Simple lexical overlap as proxy for fast semantic similarity
            claim_words = set(claim.lower().split())
            for chunk in chunks:
                chunk_words = set(chunk.lower().split())
                overlap = len(claim_words.intersection(chunk_words)) / max(len(claim_words), 1)
                if overlap > max_overlap:
                    max_overlap = overlap
                    best_chunk = chunk
                    
            if not best_chunk or max_overlap < 0.1:
                unsupported += 1
                continue
                
            # LLM Verification for the best chunk (Primary)
            prompt = f"Claim: {claim}\n\nSource: {best_chunk}\n\nDoes the source fully verify the claim, weakly support it, or not support it? Reply ONLY with 'VERIFIED', 'WEAK', or 'UNSUPPORTED'."
            decision1 = "UNSUPPORTED"
            try:
                res = await primary_judge.generate([{"role": "user", "content": prompt}], temperature=0.0)
                decision1 = res.text.strip().upper()
            except Exception:
                if max_overlap > 0.5: decision1 = "VERIFIED"
                elif max_overlap > 0.2: decision1 = "WEAK"
                
            decision2 = None
            if secondary_judge:
                try:
                    res2 = await secondary_judge.generate([{"role": "user", "content": prompt}], temperature=0.0)
                    decision2 = res2.text.strip().upper()
                except Exception:
                    decision2 = "UNAVAILABLE"

            # Resolve Dual-Judge
            final_decision = decision1
            if decision2 and decision2 != "UNAVAILABLE":
                # If they disagree, take the more conservative (weaker) evaluation
                ranks = {"VERIFIED": 3, "WEAK": 2, "UNSUPPORTED": 1}
                r1 = ranks.get(decision1, 1)
                r2 = ranks.get(decision2, 1)
                final_decision = "VERIFIED" if min(r1, r2) == 3 else ("WEAK" if min(r1, r2) == 2 else "UNSUPPORTED")
                
            if "VERIFIED" in final_decision:
                verified += 1
            elif "WEAK" in final_decision:
                weak += 1
            else:
                unsupported += 1
                
        total = len(claims) if claims else 1
        return {
            "verified": verified,
            "weak": weak,
            "unsupported": unsupported,
            "confidence": verified / total,
            "evidence_coverage": (verified + weak) / total,
            "hallucination_rate": unsupported / total
        }

