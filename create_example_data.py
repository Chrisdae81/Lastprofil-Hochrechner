#!/usr/bin/env python3
"""Generiert eine realistische Beispiel-Lastprofil-CSV für Tests."""

import numpy as np
import pandas as pd
from pathlib import Path


def create_example_load_profile():
    """Erstellt ein realistisches 15-Min-Lastprofil für ein Gewerbe mit PV."""

    # Gesamtes Jahr 2023 in 15-Min-Intervallen
    index = pd.date_range("2023-01-01 00:00", "2023-12-31 23:45", freq="15min")
    np.random.seed(42)

    n = len(index)
    hours = index.hour + index.minute / 60.0
    day_of_year = index.dayofyear

    # Grundlast: 20 kW (Gewerbe mit Kühlung, Server, etc.)
    base_load = 20.0

    # Tagesprofil: Gewerbe 7-18 Uhr höhere Last
    work_factor = np.where(
        (hours >= 7) & (hours <= 18),
        1.0 + 0.8 * np.sin(np.pi * (hours - 7) / 11),  # Glocke über Arbeitstag
        0.3,  # Nacht/Wochenende niedrig
    )

    # Wochenende reduzieren
    is_weekend = index.weekday >= 5
    work_factor = np.where(is_weekend, work_factor * 0.4, work_factor)

    # Saisonaler Faktor (Winter etwas höher wegen Beleuchtung/Heizung)
    seasonal = 1.0 + 0.15 * np.cos(2 * np.pi * (day_of_year - 15) / 365)

    # Bruttoverbrauch (ohne PV)
    gross_consumption = base_load * work_factor * seasonal

    # Rauschen hinzufügen
    noise = np.random.normal(0, 2, n)
    gross_consumption = np.maximum(gross_consumption + noise, 5.0)

    # Vereinfachte PV-Simulation (30 kWp Südausrichtung)
    kwp = 30.0
    solar_hour_angle = (hours - 12) * 15  # Grad
    solar_elevation = np.maximum(
        0, np.sin(np.radians(50)) * np.sin(np.radians(-23.45 * np.cos(np.radians(360 / 365 * (day_of_year + 10)))))
        + np.cos(np.radians(50)) * np.cos(np.radians(-23.45 * np.cos(np.radians(360 / 365 * (day_of_year + 10)))))
        * np.cos(np.radians(solar_hour_angle))
    )

    # Bewölkung simulieren
    cloud_factor = np.clip(np.random.normal(0.7, 0.25, n), 0.1, 1.0)
    pv_production = kwp * solar_elevation * cloud_factor

    # Netzbezug = Brutto - PV (mind. 0, da keine Einspeisung im Datensatz)
    net_consumption = np.maximum(gross_consumption - pv_production, 0.0)

    # DataFrame erstellen (deutsches Format)
    df = pd.DataFrame({
        "Zeitstempel": index.strftime("%d.%m.%Y %H:%M"),
        "Bezug_kW": [f"{v:.2f}".replace(".", ",") for v in net_consumption],
    })

    output_path = Path("example_data/beispiel_lastprofil.csv")
    df.to_csv(output_path, sep=";", index=False, encoding="utf-8-sig")
    print(f"Beispieldaten erstellt: {output_path}")
    print(f"  Datenpunkte: {len(df)}")
    print(f"  Zeitraum: {index[0]} bis {index[-1]}")
    print(f"  Mittlerer Netzbezug: {np.mean(net_consumption):.1f} kW")
    print(f"  Max. Netzbezug: {np.max(net_consumption):.1f} kW")


if __name__ == "__main__":
    create_example_data = create_example_load_profile
    create_example_data()
