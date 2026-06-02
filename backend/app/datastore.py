"""Data-access layer for the PartSelect catalog.

Each public method here maps 1:1 to an agent tool. The agent never touches raw
data — it calls these, so swapping the JSON seed for a real database or a
scraped catalog later is a change in this file only.
"""
import json
from pathlib import Path
from typing import Optional

from .models import Part, ApplianceModel, CompatibilityResult, ApplianceType

DATA_DIR = Path(__file__).parent / "data"


def _norm(s: str) -> str:
    return s.strip().upper()


class DataStore:
    def __init__(self) -> None:
        parts_raw = json.loads((DATA_DIR / "parts.json").read_text())
        models_raw = json.loads((DATA_DIR / "models.json").read_text())
        self.parts: dict[str, Part] = {_norm(p["ps_number"]): Part(**p) for p in parts_raw}
        self.models: dict[str, ApplianceModel] = {
            _norm(m["model_number"]): ApplianceModel(**m) for m in models_raw
        }

    # -- direct lookups ----------------------------------------------------
    def get_part(self, ps_number: str) -> Optional[Part]:
        return self.parts.get(_norm(ps_number))

    def get_model(self, model_number: str) -> Optional[ApplianceModel]:
        return self.models.get(_norm(model_number))

    # -- search ------------------------------------------------------------
    def search_parts(
        self, query: str, appliance_type: Optional[ApplianceType] = None, limit: int = 5
    ) -> list[Part]:
        """Lightweight keyword scorer. In production this is where the vector
        store takes over for semantic matches; the interface stays identical."""
        q = query.lower().strip()
        words = [w for w in q.split() if w]
        scored: list[tuple[int, Part]] = []
        for p in self.parts.values():
            if appliance_type and p.appliance_type != appliance_type:
                continue
            hay = " ".join(
                [p.name, p.category, p.brand, p.ps_number, p.mfr_part_number]
                + p.symptoms_fixed
                + p.compatible_brands
            ).lower()
            score = (2 if q and q in hay else 0) + sum(1 for w in words if w in hay)
            if score:
                scored.append((score, p))
        scored.sort(key=lambda t: (t[0], t[1].review_count), reverse=True)
        return [p for _, p in scored[:limit]]

    # -- compatibility -----------------------------------------------------
    def check_compatibility(self, ps_number: str, model_number: str) -> CompatibilityResult:
        part = self.get_part(ps_number)
        model = self.get_model(model_number)
        ps, mn = _norm(ps_number), _norm(model_number)

        if not part:
            return CompatibilityResult(
                compatible=None, part_number=ps, model_number=mn,
                reason=f"I couldn't find part {ps} in the catalog.",
            )

        # Unknown model: fall back to the part's own compatibility list.
        if not model:
            if mn in [_norm(m) for m in part.compatible_models]:
                return CompatibilityResult(
                    compatible=True, part_number=ps, model_number=mn, part=part,
                    reason=f"{ps} lists {mn} as a compatible model.",
                )
            return CompatibilityResult(
                compatible=None, part_number=ps, model_number=mn, part=part,
                reason=(f"I don't have model {mn} on file, so I can't fully confirm fit. "
                        f"This part fits {part.appliance_type.value}s."),
            )

        # The key check: a refrigerator part can never fit a dishwasher.
        if part.appliance_type != model.appliance_type:
            return CompatibilityResult(
                compatible=False, part_number=ps, model_number=mn, part=part,
                reason=(f"This part fits {part.appliance_type.value}s, "
                        f"but {mn} is a {model.appliance_type.value}."),
            )

        listed = ps in [_norm(x) for x in model.compatible_parts] or \
            mn in [_norm(m) for m in part.compatible_models]
        if listed:
            return CompatibilityResult(
                compatible=True, part_number=ps, model_number=mn, part=part,
                reason=f"Yes — {ps} is compatible with {mn}.",
            )
        return CompatibilityResult(
            compatible=False, part_number=ps, model_number=mn, part=part,
            reason=(f"{ps} isn't listed as a match for {mn}. They're both "
                    f"{model.appliance_type.value} items, so double-check the model number."),
        )

    # -- troubleshooting ---------------------------------------------------
    def parts_for_symptom(
        self, symptom: str, appliance_type: Optional[ApplianceType] = None,
        brand: Optional[str] = None, limit: int = 5,
    ) -> list[Part]:
        s = symptom.lower().strip()
        key_words = {w for w in s.split() if len(w) > 3}

        # A word that appears in many parts' symptom lists is a weak signal
        # ("ice", "door", "water"); a rare word is a strong one ("dirty",
        # "drain", "leak"). Weight each matched word by how distinctive it is.
        word_freq: dict[str, int] = {}
        for p in self.parts.values():
            seen = {w for sym in p.symptoms_fixed for w in sym.lower().split()}
            for w in seen:
                word_freq[w] = word_freq.get(w, 0) + 1
        total_parts = max(len(self.parts), 1)

        def word_weight(w: str) -> float:
            # Rarer words count for more; very common words barely count.
            freq = word_freq.get(w, 0)
            return 1.0 if freq == 0 else max(0.1, 1.0 - freq / total_parts)

        scored: list[tuple[float, Part]] = []
        for p in self.parts.values():
            if appliance_type and p.appliance_type != appliance_type:
                continue
            if brand and brand.lower() not in [b.lower() for b in (p.compatible_brands + [p.brand])]:
                continue
            best = 0.0
            for sym in p.symptoms_fixed:
                low = sym.lower()
                if s in low or low in s:
                    score = 10.0                       # phrase containment: strong
                else:
                    matched = [w for w in key_words if w in low]
                    score = sum(word_weight(w) for w in matched)
                best = max(best, score)
            if best > 0:
                scored.append((best, p))

        if not scored:
            return []
        scored.sort(key=lambda t: (t[0], t[1].review_count), reverse=True)
        # Keep genuine matches: parts close to the best score. This drops parts
        # that only share one weak/generic word when stronger matches exist, but
        # never returns empty when something matched.
        top = scored[0][0]
        kept = [p for sc, p in scored if sc >= max(0.5, top * 0.5)]
        return kept[:limit]


store = DataStore()
