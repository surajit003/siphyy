# Siphyy Fleet — Tyre Safety Handbook

**Document version**: 2026-05-18
**Authority**: Siphyy Fleet Operations Director

---

## Internal tyre standards (stricter than legal minimums)

Our fleet operates under standards more conservative than Kenyan legal minimums:

- **Tread depth**: minimum **4.0 mm** for fleet vehicles (Kenyan legal minimum is 1.6 mm)
  - **Mombasa route**: minimum 4.5 mm due to road quality
  - **Nairobi metro routes**: minimum 3.5 mm acceptable
  - **All routes**: any tyre below 4.0 mm must be replaced within 7 days

- **Age cap**: replace any tyre older than **5 years** from date of manufacture, regardless of tread depth (no legal limit exists)

- **Sidewall**: zero tolerance for any visible sidewall damage — cracks, bulges, cuts, or cord exposure all warrant immediate replacement

## Damage categorisation table

| Damage observed | Action | Window |
|---|---|---|
| Tread depth < 4.0 mm | `schedule_replacement` | within 7 days |
| Tread depth < 2.5 mm | `replace_immediately` | within 24 hours |
| Sidewall crack visible | `replace_immediately` | same day |
| Sidewall bulge | `remove_from_service` | immediately, do not drive |
| Cord exposure | `remove_from_service` | immediately, do not drive |
| Embedded foreign object (nail, screw) | Inspect for puncture; `replace_immediately` if depth > 3mm | within 24 hours |
| Uneven wear pattern | Investigate alignment + pressure; replace if pattern severe | within 7 days |
| Tyre age > 5 years | `schedule_replacement` regardless of tread | within 14 days |

## Route-specific advisories

### Mombasa Road (Nairobi → Mombasa)
- Known pothole hazards near Mlolongo and Athi River
- Nyali Bridge approach has degraded road surface (per postmortem **INC-002**, May 2026)
- Drivers must reduce speed to 40 km/h in advisory zones
- Pre-trip tyre pressure check is **MANDATORY** for this route

### Mombasa → Malindi (coastal)
- Coastal humidity accelerates sidewall cracking
- Inspect sidewalls every 30 days regardless of tread depth

### Nairobi metropolitan
- Heavy kerbstone hazards in CBD
- Watch for wheel-arch impact wear on inner sidewalls

## Reference incidents

- **INC-002** (KCA 891H, May 2026): Front-left tyre sidewall split after pothole impact at 55 km/h on Nyali Bridge approach. Vehicle had 4mm tread — within spec at the time, but the Mombasa-route minimum has since been raised to 4.5 mm. Pressure check was made mandatory after this incident.
- **INC-007** (KAY 234X, December 2025): Front-right tyre blowout on highway. Tyre was 5.5 years old despite acceptable tread depth. The 5-year age limit was introduced after this incident.

## Recommended-action codes (use these in assessments)

| Code | When to use |
|---|---|
| `continue_use` | Passes all visual + measurement checks |
| `schedule_replacement` | Meets one or more "within 7 days" criteria from the damage table |
| `replace_immediately` | Meets one or more "within 24 hours" criteria |
| `remove_from_service` | Vehicle must not move under its own power |

## Safety score guidance (1-10)

| Score | Condition |
|---|---|
| 10 | Brand new |
| 8-9 | Good condition, no concerns |
| 6-7 | Minor wear, continue monitoring |
| 4-5 | Meaningful wear or minor damage — schedule replacement |
| 2-3 | Significant safety concern — replace immediately |
| 1 | Critical — vehicle must not move |

## Reporting standard

Every driver-submitted tyre photo must be assessed against this handbook. Assessments that deviate from these standards (e.g. recommending `continue_use` when any sidewall damage is present) trigger a senior review.

When reporting an assessment, cite the specific row from the damage categorisation table that drove the decision, e.g. *"recommendation is `replace_immediately` per the Sidewall crack row of the damage table."*
