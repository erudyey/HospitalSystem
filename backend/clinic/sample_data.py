"""Sample patient and clinical case text used only by development fixtures."""

FIRST_NAMES = [
    "Maria",
    "Jose",
    "Juan",
    "Ana",
    "Carlos",
    "Rosa",
    "Miguel",
    "Elena",
    "Luis",
    "Sofia",
    "Pedro",
    "Isabel",
    "Antonio",
    "Carmen",
    "Fernando",
    "Laura",
    "Ricardo",
    "Patricia",
    "Eduardo",
    "Gabriela",
]

LAST_NAMES = [
    "Santos",
    "Reyes",
    "Cruz",
    "Flores",
    "Garcia",
    "Torres",
    "Rivera",
    "Mendoza",
    "Ramos",
    "Dela Cruz",
    "Villanueva",
    "Gonzalez",
    "Aquino",
    "Bautista",
    "Castillo",
    "Morales",
    "Espinoza",
    "Navarro",
    "Herrera",
    "Soriano",
]

REASONS = [
    "Routine physical and wellness checkup",
    "Persistent productive cough and low-grade fever",
    "Hypertension maintenance review",
    "Follow-up for seasonal allergic rhinitis",
    "Pediatric immunization and growth review",
    "Mild epigastric discomfort after meals",
    "Headache and eye strain during screen use",
    "Prescription renewal for antidiabetic therapy",
]

CLINICAL_CASES = [
    {
        "diagnosis": "Acute Upper Respiratory Tract Infection (URTI)",
        "symptoms": "3-day history of rhinorrhea, mild sore throat, non-productive cough, afebrile.",
        "clinical_notes": "BP: 118/76 mmHg, HR: 76 bpm, Temp: 36.8C. Pharyngeal erythema present, tonsils not enlarged. Lungs clear to auscultation.",
        "prescription": "Paracetamol 500mg tab, 1 tab Q6H PRN fever/headache\nCetirizine 10mg tab, 1 tab OD at bedtime x 5 days\nSaline nasal spray, 2 sprays per nostril TID",
        "follow_up_advice": "Rest, oral rehydration (2L water/day). Return in 5 days if cough worsens or fever spikes.",
    },
    {
        "diagnosis": "Essential (Primary) Hypertension, Stage 1",
        "symptoms": "Occasional morning occipital headache, no chest pain or shortness of breath.",
        "clinical_notes": "BP: 142/90 mmHg (repeat: 140/88 mmHg), HR: 80 bpm regular. S1/S2 normal, no murmurs. Peripheral pulses intact.",
        "prescription": "Amlodipine 5mg tab, 1 tab OD every morning\nHome BP monitoring log daily",
        "follow_up_advice": "Low-salt diet (<2g sodium/day), 30 minutes brisk walking daily. Return in 2 weeks with BP log.",
    },
    {
        "diagnosis": "Acute Viral Gastroenteritis",
        "symptoms": "Watery diarrhea 4x in past 24 hours, mild nausea, no hematochezia.",
        "clinical_notes": "BP: 110/70 mmHg, HR: 84 bpm, Temp: 37.2C. Abdomen soft, hyperactive bowel sounds, mild diffuse tenderness without guarding.",
        "prescription": "Oral Rehydration Salts (ORS), 1 sachet in 1L water, drink freely\nZinc sulfate 20mg tab, 1 tab OD x 10 days\nParacetamol 500mg tab, 1 tab PRN",
        "follow_up_advice": "Bland diet (BRAT). Avoid dairy, caffeine, and fatty food. Return immediately if signs of dehydration appear.",
    },
    {
        "diagnosis": "Allergic Contact Dermatitis",
        "symptoms": "Pruritic erythematous papules and patches on bilateral forearms following garden exposure.",
        "clinical_notes": "Well-demarcated erythematous plaques with scattered microvesicles. No signs of secondary bacterial infection.",
        "prescription": "Hydrocortisone 1% cream, apply thinly BID x 7 days\nLoratadine 10mg tab, 1 tab OD in morning x 7 days",
        "follow_up_advice": "Avoid scratching, keep skin moisturized with hypoallergenic lotion. Wear protective gloves during yard work.",
    },
]

CONTACTS = [
    "09171234567",
    "09281234567",
    "09391234567",
    "09501234567",
    "09611234567",
    "09721234567",
    "(02) 8123-4567",
    "(032) 412-3456",
    "",
]
