"""CSV-Export der Ergebnisse."""

import pandas as pd
from pathlib import Path


def export_results(df: pd.DataFrame, output_path: str | Path) -> Path:
    """
    Exportiert die Ergebnisse als CSV-Datei im deutschen Format.

    Args:
        df: DataFrame mit Spalten netzbezug_kw, pv_erzeugung_kw, brutto_verbrauch_kw
        output_path: Pfad für die Ausgabedatei

    Returns:
        Pfad der erstellten Datei
    """
    output_path = Path(output_path)

    # Intervall bestimmen für kW -> kWh Umrechnung
    intervals = df.index.to_series().diff().dropna()
    hours_per_interval = intervals.median().total_seconds() / 3600

    export_df = df[["netzbezug_kw", "pv_erzeugung_kw", "brutto_verbrauch_kw"]].copy()
    # kW -> kWh pro Intervall umrechnen, damit Excel-SUM direkt kWh ergibt
    export_df = export_df * hours_per_interval
    export_df.columns = ["Netzbezug_kWh", "PV_Erzeugung_kWh", "Brutto_Verbrauch_kWh"]
    export_df.index.name = "Zeitstempel"

    # Werte auf 3 Dezimalstellen runden
    export_df = export_df.round(3)

    export_df.to_csv(
        output_path,
        sep=";",
        decimal=",",
        date_format="%d.%m.%Y %H:%M",
    )

    print(f"\n  Ergebnis gespeichert: {output_path}")
    print(f"  Datenpunkte: {len(export_df)}")
    return output_path
