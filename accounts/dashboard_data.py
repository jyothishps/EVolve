import json
from datetime import timedelta

from django.db.models import Count, Q, Sum
from django.db.models.functions import ExtractHour
from django.utils import timezone

from bookings.models import Booking
from sessions_app.models import ChargingSession
from stations.models import ChargingSlot as Slot
from ml_prediction.config import classify_load


def _predicted_load_by_hour(today):
    """Average ML-predicted load per hour over upcoming open slots (Estimated)."""
    try:
        from ml_prediction.predictor import predict_slots

        slots = list(Slot.objects.filter(date__gte=today, status="Available").select_related('station', 'charger')[:300])
        if not slots:
            return [], [], []
        preds = predict_slots(slots)
        buckets = {}
        for slot in slots:
            p = preds.get(slot.id)
            if p and p.get("available"):
                buckets.setdefault(slot.start_time.hour, []).append(p["load_kw"])
        hours = sorted(buckets)
        loads = [round(sum(buckets[h]) / len(buckets[h]), 1) for h in hours]
        levels = [classify_load(v) for v in loads]
        return [f"{h:02d}:00" for h in hours], loads, levels
    except Exception:
        return [], [], []


def build_dashboard_analytics():
    today = timezone.localdate()

    # Bookings by slot date, 7 days back to 7 days ahead
    days = [today + timedelta(days=i) for i in range(-7, 8)]
    per_day = {
        r["booking_date"]: r["n"]
        for r in Booking.objects.filter(booking_date__in=days)
        .values("booking_date")
        .annotate(n=Count("id"))
    }
    trend_labels = [d.strftime("%d %b") for d in days]
    trend_values = [per_day.get(d, 0) for d in days]

    # Status split
    status_rows = list(Booking.objects.values("status").annotate(n=Count("id")).order_by("-n"))

    # Station usage, top 8
    usage_rows = list(
        Booking.objects.values("station__station_code")
        .annotate(n=Count("id"))
        .order_by("-n")[:8]
    )

    # Payments (Booking fee)
    pay = Booking.objects.aggregate(
        paid=Sum("booking_fee", filter=Q(payment_status="Paid")),
        refunded=Sum("booking_fee", filter=Q(payment_status="Refunded")),
        forfeited=Sum("booking_fee", filter=Q(payment_status="Forfeited")),
    )
    paid = float(pay["paid"] or 0)
    refunded = float(pay["refunded"] or 0)
    forfeited = float(pay["forfeited"] or 0)

    # Sessions & Charging Revenue
    sess = ChargingSession.objects.aggregate(
        n=Count("id"),
        energy=Sum("energy_kWh"),
        charging_revenue=Sum("amount", filter=Q(payment_status="Paid")),
    )
    charging_revenue = float(sess["charging_revenue"] or 0)

    # Predicted load
    ph_labels, ph_values, ph_levels = _predicted_load_by_hour(today)

    chart_data = {
        "trend": {"labels": trend_labels, "values": trend_values},
        "status": {
            "labels": [r["status"] for r in status_rows],
            "values": [r["n"] for r in status_rows],
        },
        "usage": {
            "labels": [r["station__station_code"] for r in usage_rows],
            "values": [r["n"] for r in usage_rows],
        },
        "payments": {
            "labels": ["Collected", "Refunded", "Forfeited (no-show)"],
            "values": [paid, refunded, forfeited],
        },
        "load": {"labels": ph_labels, "values": ph_values, "levels": ph_levels},
    }

    return {
        "chart_data": chart_data,
        "chart_data_json": json.dumps(chart_data),
        "total_sessions": sess["n"] or 0,
        "total_energy": round(float(sess["energy"] or 0), 1),
        "total_revenue": round(paid + forfeited + charging_revenue, 2),
        "revenue_collected": paid,
        "revenue_refunded": refunded,
        "revenue_forfeited": forfeited,
        "reservation_revenue": paid + forfeited,
        "charging_revenue": charging_revenue,
    }