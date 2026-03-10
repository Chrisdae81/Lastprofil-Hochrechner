"""PV-Simulation: Interpolation und Brutto-Verbrauch-Berechnung."""

import pandas as pd
import numpy as np


def simulate_gross_consumption(
    load_profile: pd.DataFrame,
    pv_production: pd.DataFrame,
) -> pd.DataFrame:
    """
    Berechnet den Brutto-Verbrauch durch Addition von Netzbezug und PV-Erzeugung.

    Args:
        load_profile: DataFrame mit DatetimeIndex und Spalte 'netzbezug_kw'
        pv_production: DataFrame mit DatetimeIndex und Spalte 'pv_kw' (stündlich)

    Returns:
        DataFrame mit Spalten: netzbezug_kw, pv_erzeugung_kw, brutto_verbrauch_kw
    """
    # Intervall des Lastprofils bestimmen
    lp_intervals = load_profile.index.to_series().diff().dropna()
    lp_interval = lp_intervals.median()

    # PV-Daten auf das Lastprofil-Intervall interpolieren
    pv_interpolated = _interpolate_pv_to_load(pv_production, load_profile.index, lp_interval)

    # PV-Daten auf Lastprofil-Zeitraum mappen (Jahr-Matching)
    pv_mapped = _map_pv_to_load_period(pv_interpolated, load_profile)

    # Brutto-Verbrauch berechnen
    result = load_profile.copy()
    result["pv_erzeugung_kw"] = pv_mapped
    result["brutto_verbrauch_kw"] = result["netzbezug_kw"] + result["pv_erzeugung_kw"]

    # Statistiken ausgeben
    _print_summary(result)

    return result


def _interpolate_pv_to_load(
    pv: pd.DataFrame,
    target_index: pd.DatetimeIndex,
    target_interval: pd.Timedelta,
) -> pd.DataFrame:
    """Interpoliert stündliche PV-Daten auf das Ziel-Intervall."""
    pv_interval = pv.index.to_series().diff().dropna().median()

    if pv_interval <= target_interval:
        # PV-Daten sind bereits feiner oder gleich -> kein Upsampling nötig
        return pv

    # Auf Ziel-Intervall resampled und linear interpoliert
    pv_resampled = pv.resample(target_interval).interpolate(method="linear")

    print(f"  PV-Daten interpoliert: {pv_interval} -> {target_interval}")
    return pv_resampled


def _map_pv_to_load_period(
    pv: pd.DataFrame,
    load: pd.DataFrame,
) -> pd.Series:
    """
    Mappt PV-Erzeugungsdaten auf den Zeitraum des Lastprofils.

    Da TMY-Daten ein anderes Jahr haben können als das Lastprofil,
    wird nach Monat/Tag/Stunde/Minute gemappt.
    """
    # Lookup-Key erstellen: (Monat, Tag, Stunde, Minute)
    pv_lookup = {}
    for ts, row in pv.iterrows():
        key = (ts.month, ts.day, ts.hour, ts.minute)
        pv_lookup[key] = row["pv_kw"]

    # PV-Werte für jeden Lastprofil-Zeitpunkt finden
    pv_values = []
    missing_count = 0
    for ts in load.index:
        key = (ts.month, ts.day, ts.hour, ts.minute)
        value = pv_lookup.get(key, 0.0)
        if key not in pv_lookup:
            missing_count += 1
        pv_values.append(max(value, 0.0))  # PV kann nicht negativ sein

    if missing_count > 0:
        total = len(load)
        print(f"  Hinweis: {missing_count}/{total} Zeitpunkte ohne PV-Daten "
              f"(z.B. 29. Feb) -> auf 0 gesetzt.")

    return pd.Series(pv_values, index=load.index, name="pv_erzeugung_kw")


def _print_summary(result: pd.DataFrame) -> None:
    """Gibt eine Zusammenfassung der Ergebnisse aus."""
    # Zeitintervall für kWh-Umrechnung
    intervals = result.index.to_series().diff().dropna()
    hours_per_interval = intervals.median().total_seconds() / 3600

    netzbezug_kwh = (result["netzbezug_kw"] * hours_per_interval).sum()
    pv_kwh = (result["pv_erzeugung_kw"] * hours_per_interval).sum()
    brutto_kwh = (result["brutto_verbrauch_kw"] * hours_per_interval).sum()

    print("\n" + "=" * 60)
    print("  ZUSAMMENFASSUNG")
    print("=" * 60)
    print(f"  Netzbezug (gemessen):      {netzbezug_kwh:>10,.0f} kWh")
    print(f"  PV-Erzeugung (simuliert):  {pv_kwh:>10,.0f} kWh")
    print(f"  Brutto-Verbrauch:          {brutto_kwh:>10,.0f} kWh")
    print(f"  PV-Anteil am Brutto:       {pv_kwh / brutto_kwh * 100:>10.1f} %"
          if brutto_kwh > 0 else "")
    print(f"  Max. Netzbezug:            {result['netzbezug_kw'].max():>10.1f} kW")
    print(f"  Max. PV-Erzeugung:         {result['pv_erzeugung_kw'].max():>10.1f} kW")
    print(f"  Max. Brutto-Verbrauch:     {result['brutto_verbrauch_kw'].max():>10.1f} kW")
    print("=" * 60)
