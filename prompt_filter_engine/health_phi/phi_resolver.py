from typing import List, Dict


class PHIResolver:
    """
    Pairs medical_condition and medication_name entities that share the same
    therapeutic_area, setting an effective_tier = max(tier_condition, tier_medication).

    Rules (from PDF §4.1):
      1. Same therapeutic_area  → confirmed pair, use max tier
      2. Different therapeutic_area → treat independently
      3. Single entity (no counterpart) → treat independently
    """

    def resolve(self, entities: List[Dict]) -> List[Dict]:
        """
        Args:
            entities: Enriched entity list (may contain any label type).
                      Health entities must have context['tier'] and
                      context['therapeutic_area'] already set.
        Returns:
            Same entity list with 'paired' and 'effective_tier' added to
            matched health entities. Non-health entities are passed through
            unchanged.
        """
        # Separate health entities from the rest
        health_labels = {"medical_condition", "medication_name"}
        health_entities = [e for e in entities if e["label"] in health_labels]
        other_entities  = [e for e in entities if e["label"] not in health_labels]

        conditions  = [e for e in health_entities if e["label"] == "medical_condition"]
        medications = [e for e in health_entities if e["label"] == "medication_name"]

        paired_conditions  = set()
        paired_medications = set()

        # Try to pair each condition with a medication sharing the same TA
        for i, cond in enumerate(conditions):
            cond_ta   = (cond.get("context") or {}).get("therapeutic_area")
            cond_tier = (cond.get("context") or {}).get("tier") or 1

            if not cond_ta:
                continue  # Cannot pair without a therapeutic_area

            for j, med in enumerate(medications):
                if j in paired_medications:
                    continue  # Already paired

                med_ta   = (med.get("context") or {}).get("therapeutic_area")
                med_tier = (med.get("context") or {}).get("tier") or 1

                if cond_ta == med_ta:
                    # Confirmed pair
                    effective_tier = max(cond_tier, med_tier)

                    cond["paired"]         = True
                    cond["effective_tier"] = effective_tier
                    med["paired"]          = True
                    med["effective_tier"]  = effective_tier

                    paired_conditions.add(i)
                    paired_medications.add(j)
                    print(
                        f"[PHIResolver] Paired '{cond['text']}' (condition) with "
                        f"'{med['text']}' (medication) — TA: {cond_ta}, Tier: {effective_tier}"
                    )
                    break  # One-to-one pairing

        # Unpaired health entities — tag independently
        for i, cond in enumerate(conditions):
            if i not in paired_conditions:
                tier = (cond.get("context") or {}).get("tier") or 1
                cond["paired"]         = False
                cond["effective_tier"] = tier

        for j, med in enumerate(medications):
            if j not in paired_medications:
                tier = (med.get("context") or {}).get("tier") or 1
                med["paired"]         = False
                med["effective_tier"] = tier

        # Reconstruct full entity list preserving original order
        result = []
        h_idx = {id(e): e for e in health_entities}
        for e in entities:
            if id(e) in h_idx:
                result.append(h_idx[id(e)])
            else:
                result.append(e)
        return result
