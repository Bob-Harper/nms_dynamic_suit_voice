# logitsprocessor.py (or inline for your test)
from transformers import LogitsProcessor
import torch

class ThinkClampProcessor(LogitsProcessor):
    """
    Shorten <think> by biasing closing tag and penalizing ramble tokens after a soft limit.
    Leaves everything else untouched. Stateless across batches, state derived from input_ids.
    """
    def __init__(self, tokenizer, soft_limit=32, close_boost=8.0, ramble_penalty=-6.0, ramble_words=None):
        self.tok = tokenizer
        self.soft_limit = soft_limit
        self.close_boost = close_boost
        self.ramble_penalty = ramble_penalty

        # Special token ids for <think> and </think>
        self.open_id = self._get_id("<think>")
        self.close_id = self._get_id("</think>")

        # Small, surgical set of ramble openers (don’t ban function words in production)
        ramble_words = ramble_words or ["Okay", "So", "Let's", "First", "Now", "Well"]
        # Tokenize to single-token ids where possible; keep only first piece to avoid overreach
        ids = set()
        for w in ramble_words:
            ids_list = self.tok.encode(w, add_special_tokens=False)
            if ids_list:
                ids.add(ids_list[0])
            # also leading-space variant common in BPEs
            ids_list2 = self.tok.encode(" " + w, add_special_tokens=False)
            if ids_list2:
                ids.add(ids_list2[0])
        self.ramble_ids = torch.tensor(sorted(ids), dtype=torch.long)

    def _get_id(self, token_str):
        tid = self.tok.convert_tokens_to_ids(token_str)
        if tid is None or tid == self.tok.unk_token_id:
            # Fallback: many Qwen “thinking” builds still use real special ids; last resort: hardcode if you know it
            # e.g., </think> was 151668 in your test
            if token_str == "</think>":
                return 151668
            elif token_str == "<think>":
                # put your known <think> id here if needed
                return self.tok.unk_token_id
        return tid

    def __call__(self, input_ids: torch.LongTensor, scores: torch.FloatTensor) -> torch.FloatTensor:
        # input_ids: [bsz, seq]; scores: [bsz, vocab]
        bsz = input_ids.size(0)
        device = scores.device

        # Nothing to do if we can't identify </think>
        if self.close_id is None or self.close_id < 0:
            return scores

        # Vectorized-ish loop over batch to avoid Python hot path per token
        for b in range(bsz):
            seq = input_ids[b]

            # Are we inside a <think> ... </think> span?
            # Find last occurrence of <think> and </think>
            # Note: ids are int, so compare directly
            open_positions = (seq == self.open_id).nonzero()
            close_positions = (seq == self.close_id).nonzero()

            if open_positions.numel() == 0:
                continue  # never entered think; do nothing

            last_open = int(open_positions[-1])
            last_close = int(close_positions[-1]) if close_positions.numel() > 0 else -1

            inside_think = (last_open > last_close)

            if not inside_think:
                continue  # already closed; do nothing

            # Count how many tokens have been generated since last <think>
            think_len = seq.size(0) - (last_open + 1)

            if think_len >= self.soft_limit:
                # 1) Strongly encourage closing tag
                scores[b, self.close_id] += self.close_boost

                # 2) Discourage ramble openers
                if self.ramble_ids.numel() > 0:
                    idx = self.ramble_ids.to(device)
                    scores[b, idx] += self.ramble_penalty

        return scores
