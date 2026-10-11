from .config import LEVEL_RANK, TIE_MARGIN_KW


def rank_slots(slots):
    """
    Simple, explainable rules. Each slot must already have .prediction.

    1. Sort: Low first, then Normal, then Peak. Same level: earlier date/time first.
    2. Lowest predicted load = best. Any slot within 3 kW of it (and not Peak)
       is tagged 'Recommended'.
    3. Peak slots are tagged 'Avoid' only if a non-Peak option exists.
    4. Slots without a prediction go last, untagged.

    Returns (ranked_slots, best_slot_or_None).
    """
    predicted = [s for s in slots if s.prediction['available']]
    unpredicted = [s for s in slots if not s.prediction['available']]

    for s in slots:
        s.tag = ''

    best = None
    if predicted:
        min_load = min(s.prediction['load_kw'] for s in predicted)
        has_non_peak = any(s.prediction['level'] != 'Peak' for s in predicted)

        for s in predicted:
            level = s.prediction['level']
            if level != 'Peak' and s.prediction['load_kw'] <= min_load + TIE_MARGIN_KW:
                s.tag = 'Recommended'
            elif level == 'Peak' and has_non_peak:
                s.tag = 'Avoid'

        predicted.sort(key=lambda s: (LEVEL_RANK[s.prediction['level']], s.date, s.start_time))
        recommended = [s for s in predicted if s.tag == 'Recommended']
        if recommended:
            best = min(recommended, key=lambda s: (s.date, s.start_time))

    return predicted + unpredicted, best