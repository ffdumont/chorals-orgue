"""Audit d'un ODF GrandOrgue: detecte les sections et cles orphelines.

Un ODF (Organ Definition File) est un fichier INI-like. GrandOrgue ne charge
que les sections atteignables depuis [Organ] via les declarations NumberOfXxx
et les mappings des Panels et Manuals. Les sections presentes mais non
referencees provoquent des warnings "Element ODF non utilise" au chargement.

Usage:
    python audit_odf.py <fichier.organ>                     # rapport seulement
    python audit_odf.py <fichier.organ> --write <sortie>    # ecrit version nettoyee

Strategie:
1. Parser le fichier en sections ordonnees (liste de (nom, OrderedDict, blanc_final)).
2. Construire le graphe d'atteignabilite a partir de [Organ]:
   - [Organ] declare NumberOfEnclosures, NumberOfWindchestGroups, NumberOfSwitches,
     NumberOfRanks, NumberOfPanels, NumberOfImages, NumberOfTremulants,
     NumberOfReversiblePistons, NumberOfLabels, NumberOfGenerals,
     NumberOfDivisionalCouplers, NumberOfSetterElements, NumberOfManuals
   - Chaque [ManualNNN] declare NumberOfStops/Couplers/Divisionals/Tremulants/Switches
     et mappe StopXXX=IDX, CouplerXXX=IDX, etc.
   - Chaque [PanelNNN] declare NumberOf<Type> et mappe <Type>XXX=IDX
   - Chaque Panel cree des sections overlay [PanelNNN<Type>XXX] pour chaque
     element visible, atteignables par combinaison (panel, type, idx-local).
   - Les [CouplerNNN] referencent des switches via SwitchXXX=IDX.
   - Les [StopNNN] referencent des ranks via RankXXX=IDX (et pipes).
   - [ReversiblePistonNNN] reference ObjectType/ObjectNumber.
3. Une section est orpheline si elle n'est pas atteignable.
"""
from __future__ import annotations

import argparse
import re
import sys
from collections import OrderedDict
from pathlib import Path
from typing import Dict, List, Set, Tuple


SectionName = str
Section = "OrderedDict[str, str]"
ParsedFile = List[Tuple[SectionName, Section, List[str]]]
# (nom, dict cles->valeurs, lignes blanches/commentaires apres la section)


# Types listes dans [Organ]
GLOBAL_COUNT_TYPES = {
    "NumberOfEnclosures": "Enclosure",
    "NumberOfWindchestGroups": "WindchestGroup",
    "NumberOfSwitches": "Switch",
    "NumberOfRanks": "Rank",
    "NumberOfPanels": "Panel",
    "NumberOfImages": "Image",
    "NumberOfTremulants": "Tremulant",
    "NumberOfReversiblePistons": "ReversiblePiston",
    "NumberOfLabels": "Label",
    "NumberOfGenerals": "General",
    "NumberOfDivisionalCouplers": "DivisionalCoupler",
    "NumberOfSetterElements": "SetterElement",
}

# Pluriels anglais utilises dans les cles NumberOf<Plural>
PLURAL: Dict[str, str] = {
    "Stop": "Stops",
    "Coupler": "Couplers",
    "Divisional": "Divisionals",
    "Tremulant": "Tremulants",
    "Switch": "Switches",
    "Enclosure": "Enclosures",
    "Image": "Images",
    "Label": "Labels",
    "General": "Generals",
    "DivisionalCoupler": "DivisionalCouplers",
    "ReversiblePiston": "ReversiblePistons",
    "SetterElement": "SetterElements",
    "Rank": "Ranks",
    "WindchestGroup": "WindchestGroups",
    "Panel": "Panels",
    "Manual": "Manuals",
}

# Types presents dans [ManualNNN] (references globales)
MANUAL_REF_TYPES = ("Stop", "Coupler", "Divisional", "Tremulant", "Switch")

# Types presents dans [PanelNNN] (mappent l'index local vers l'index global)
PANEL_REF_TYPES = (
    "Stop", "Coupler", "Divisional", "Tremulant", "Switch",
    "Enclosure", "Image", "Label", "General", "DivisionalCoupler",
    "ReversiblePiston", "SetterElement",
)


def count_key(t: str) -> str:
    return f"NumberOf{PLURAL.get(t, t + 's')}"


def parse_odf(path: Path) -> ParsedFile:
    """Parse un ODF en liste ordonnee de (section, cles, trailing_blanks)."""
    sections: ParsedFile = []
    current_name: str = ""
    current_data: "OrderedDict[str, str]" = OrderedDict()
    current_trailing: List[str] = []
    preamble: List[str] = []

    section_re = re.compile(r"^\[([^\]]+)\]\s*$")

    with path.open("r", encoding="utf-8-sig", errors="replace", newline="") as fh:
        for raw in fh:
            line = raw.rstrip("\r\n")
            m = section_re.match(line)
            if m:
                if current_name:
                    sections.append((current_name, current_data, current_trailing))
                else:
                    # Lignes avant toute section (doit etre vide ou blancs)
                    preamble = current_trailing[:]
                current_name = m.group(1)
                current_data = OrderedDict()
                current_trailing = []
            elif line.strip() == "":
                current_trailing.append(line)
            elif "=" in line:
                key, _, value = line.partition("=")
                current_data[key.strip()] = value
            else:
                # Commentaire ou ligne non conforme -> on la garde avec la section
                current_trailing.append(line)
        if current_name:
            sections.append((current_name, current_data, current_trailing))

    if preamble:
        # Inserer le preambule en tete avec une section "fantome"
        sections.insert(0, ("__preamble__", OrderedDict(), preamble))
    return sections


def section_dict(sections: ParsedFile) -> Dict[str, Section]:
    return {name: data for name, data, _ in sections if name != "__preamble__"}


def get_int(d: Section, key: str, default: int = 0) -> int:
    v = d.get(key)
    if v is None:
        return default
    try:
        return int(v.strip())
    except ValueError:
        return default


def get_ref(d: Section, key: str) -> int | None:
    """Lit une cle du type 'Stop001=012' et retourne 12."""
    v = d.get(key)
    if v is None:
        return None
    try:
        return int(v.strip())
    except ValueError:
        return None


def name_of(t: str, idx: int, width: int = 3) -> str:
    return f"{t}{idx:0{width}d}"


def compute_reachable(sections: ParsedFile) -> Set[str]:
    """Retourne le set des noms de sections atteignables depuis [Organ]."""
    sd = section_dict(sections)
    reachable: Set[str] = set()
    if "Organ" not in sd:
        return reachable

    organ = sd["Organ"]
    reachable.add("Organ")

    # Elements globaux declares dans [Organ]
    for ck, type_name in GLOBAL_COUNT_TYPES.items():
        n = get_int(organ, ck, 0)
        for i in range(1, n + 1):
            reachable.add(name_of(type_name, i))

    # Manuals : Manual000 = pedale si HasPedals=Y, puis Manual001..NumberOfManuals
    num_manuals = get_int(organ, "NumberOfManuals", 0)
    has_pedals = organ.get("HasPedals", "N").strip().upper() == "Y"
    manual_indices: List[int] = []
    if has_pedals:
        manual_indices.append(0)
    manual_indices.extend(range(1, num_manuals + 1))

    for mi in manual_indices:
        mname = name_of("Manual", mi)
        if mname not in sd:
            continue
        reachable.add(mname)
        mdata = sd[mname]
        for t in MANUAL_REF_TYPES:
            n = get_int(mdata, count_key(t), 0)
            for i in range(1, n + 1):
                ref = get_ref(mdata, f"{t}{i:03d}")
                if ref is not None:
                    reachable.add(name_of(t, ref))

    # Panels : 001..NumberOfPanels (deja ajoutes) + overlay sections PanelNNN<Type>XXX
    num_panels = get_int(organ, "NumberOfPanels", 0)
    for pi in range(1, num_panels + 1):
        pname = name_of("Panel", pi)
        if pname not in sd:
            continue
        pdata = sd[pname]
        for t in PANEL_REF_TYPES:
            n = get_int(pdata, count_key(t), 0)
            for i in range(1, n + 1):
                ref = get_ref(pdata, f"{t}{i:03d}")
                if ref is None:
                    # Cas sans mapping (ex: Image sans renumerotation): index local == global
                    ref = i
                # L'element global devient atteignable
                reachable.add(name_of(t, ref))
                # Overlay section : PanelNNN<Type>GGG (GGG = index global)
                reachable.add(f"{pname}{t}{ref:03d}")

    # Propagation: Couplers referencent des switches via SwitchCount/SwitchXXX
    # Stops/Couplers peuvent referencer des ranks. On itere jusqu'au point fixe.
    changed = True
    while changed:
        changed = False
        snapshot = set(reachable)
        for name in snapshot:
            if name not in sd:
                continue
            data = sd[name]
            # SwitchCount / SwitchXXX (Couplers, Stops, Tremulants, Generals...)
            sc = get_int(data, "SwitchCount", 0)
            for i in range(1, sc + 1):
                ref = get_ref(data, f"Switch{i:03d}")
                if ref is not None:
                    new = name_of("Switch", ref)
                    if new not in reachable:
                        reachable.add(new)
                        changed = True
            # Stops referencent des Ranks via NumberOfRanks + RankXXX
            nr = get_int(data, "NumberOfRanks", 0)
            for i in range(1, nr + 1):
                ref = get_ref(data, f"Rank{i:03d}")
                if ref is not None:
                    new = name_of("Rank", ref)
                    if new not in reachable:
                        reachable.add(new)
                        changed = True
            # Ranks referencent des WindchestGroups via WindchestGroup=NN
            wg = get_ref(data, "WindchestGroup")
            if wg is not None:
                new = name_of("WindchestGroup", wg)
                if new not in reachable:
                    reachable.add(new)
                    changed = True
            # ReversiblePiston: ObjectType=SWITCH, ObjectNumber=NN
            obj_type = data.get("ObjectType", "").strip().upper()
            obj_num = get_ref(data, "ObjectNumber")
            if obj_num is not None and obj_type:
                type_map = {
                    "SWITCH": "Switch",
                    "STOP": "Stop",
                    "COUPLER": "Coupler",
                    "TREMULANT": "Tremulant",
                }
                if obj_type in type_map:
                    new = name_of(type_map[obj_type], obj_num)
                    if new not in reachable:
                        reachable.add(new)
                        changed = True

    return reachable


# Cles connues comme obsoletes/non lues par GrandOrgue, par type de section.
# GrandOrgue emet un warning "Element ODF non utilise" pour chaque occurrence.
DEPRECATED_KEY_PATTERNS: Dict[str, List[re.Pattern]] = {
    "Rank": [
        # Pipe<N>ReleaseCrossfadeLength sans index de release : remplacee dans
        # les versions recentes par les attributs per-release (ReleaseMMM...).
        re.compile(r"^Pipe\d+ReleaseCrossfadeLength$"),
    ],
}


def find_orphan_keys(section_name: str, data: Section) -> List[str]:
    """Cles orphelines: numerotees au-dela d'un compteur, ou cles obsoletes.

    Exemple 1: BitmapCount=101 mais Bitmap102=... -> Bitmap102 est orpheline.
    Exemple 2: PipeXXXReleaseCrossfadeLength dans un Rank -> cle obsolete.
    """
    orphans: List[str] = []

    # Cles obsoletes connues (detectees par type de section)
    type_match = re.match(r"^([A-Za-z]+?)\d+$", section_name)
    if type_match:
        stype = type_match.group(1)
        patterns = DEPRECATED_KEY_PATTERNS.get(stype, [])
        for key in data.keys():
            for pat in patterns:
                if pat.match(key):
                    orphans.append(key)
                    break
    # Mapping de compteurs -> prefixes indexes associes
    count_patterns: List[Tuple[str, List[str]]] = [
        ("BitmapCount", ["Bitmap"]),
        ("NumberOfLogicalPipes", ["Pipe"]),
        ("NumberOfAccessiblePipes", []),  # purement informatif
        ("NumberOfLogicalKeys", ["DisplayKey", "Key"]),
        ("NumberOfAccessibleKeys", []),
        ("NumberOfRanks", ["Rank"]),
        ("SwitchCount", ["Switch"]),
        ("NumberOfStops", ["Stop"]),
        ("NumberOfCouplers", ["Coupler"]),
        ("NumberOfDivisionals", ["Divisional"]),
        ("NumberOfTremulants", ["Tremulant"]),
        ("NumberOfSwitches", ["Switch"]),
        ("NumberOfEnclosures", ["Enclosure"]),
        ("NumberOfImages", ["Image"]),
        ("NumberOfLabels", ["Label"]),
        ("NumberOfGenerals", ["General"]),
        ("NumberOfReversiblePistons", ["ReversiblePiston"]),
        ("NumberOfSetterElements", ["SetterElement"]),
        ("NumberOfDivisionalCouplers", ["DivisionalCoupler"]),
    ]

    for ck, prefixes in count_patterns:
        if not prefixes or ck not in data:
            continue
        n = get_int(data, ck, 0)
        for prefix in prefixes:
            rx = re.compile(rf"^{prefix}(\d+)(.*)$")
            for key in list(data.keys()):
                m = rx.match(key)
                if not m:
                    continue
                idx = int(m.group(1))
                if idx > n:
                    orphans.append(key)
    return orphans


def audit(sections: ParsedFile) -> Tuple[Set[str], List[str], Dict[str, List[str]]]:
    reachable = compute_reachable(sections)
    orphan_sections: List[str] = []
    orphan_keys: Dict[str, List[str]] = {}
    for name, data, _ in sections:
        if name == "__preamble__":
            continue
        if name not in reachable:
            orphan_sections.append(name)
            continue
        ok = find_orphan_keys(name, data)
        if ok:
            orphan_keys[name] = ok
    return reachable, orphan_sections, orphan_keys


def write_cleaned(sections: ParsedFile, path: Path, reachable: Set[str],
                  orphan_keys: Dict[str, List[str]], bom: bool = True) -> None:
    """Ecrit une version nettoyee en retirant sections et cles orphelines.

    Preserve l'encodage UTF-8 et les fins de ligne LF-only de l'original
    de Piotr Grabowski.
    """
    # newline="" desactive la traduction de fin de ligne: on ecrit \n tel quel.
    with path.open("w", encoding="utf-8", newline="") as fh:
        if bom:
            fh.write("﻿")
        for name, data, trailing in sections:
            if name == "__preamble__":
                for line in trailing:
                    fh.write(line + "\n")
                continue
            if name not in reachable:
                continue
            fh.write(f"[{name}]\n")
            skip_keys = set(orphan_keys.get(name, []))
            for key, value in data.items():
                if key in skip_keys:
                    continue
                fh.write(f"{key}={value}\n")
            for line in trailing:
                fh.write(line + "\n")


def main() -> int:
    ap = argparse.ArgumentParser(description="Audit ODF GrandOrgue")
    ap.add_argument("odf", type=Path)
    ap.add_argument("--write", type=Path, help="Ecrire une version nettoyee")
    ap.add_argument("--limit", type=int, default=50,
                    help="Nb max de lignes listees par categorie dans le rapport")
    args = ap.parse_args()

    if not args.odf.exists():
        print(f"Fichier introuvable: {args.odf}", file=sys.stderr)
        return 2

    sections = parse_odf(args.odf)
    total = sum(1 for name, _, _ in sections if name != "__preamble__")
    reachable, orphan_sections, orphan_keys = audit(sections)

    print(f"Fichier: {args.odf}")
    print(f"Sections totales:    {total}")
    print(f"Sections atteignables: {len(reachable)}")
    print(f"Sections orphelines: {len(orphan_sections)}")
    orphan_key_total = sum(len(v) for v in orphan_keys.values())
    print(f"Cles orphelines:     {orphan_key_total} (sur {len(orphan_keys)} sections)")
    print()

    if orphan_sections:
        # Regrouper par type en extrayant le prefixe typologique.
        # Formats: "Switch012", "Panel004Switch030", "Rank007"
        by_type: Dict[str, List[str]] = {}
        overlay_re = re.compile(r"^(Panel\d+)([A-Za-z]+)(\d+)$")
        plain_re = re.compile(r"^([A-Za-z]+?)(\d+)$")
        for name in orphan_sections:
            m = overlay_re.match(name)
            if m:
                t = f"{m.group(1)}<*>"  # ex: "Panel004<*>" pour overlays
                # Plus lisible: regrouper tous overlays par type d'element
                t = f"Panel*/{m.group(2)}"
            else:
                m2 = plain_re.match(name)
                t = m2.group(1) if m2 else name
            by_type.setdefault(t, []).append(name)
        print("=== Sections orphelines par type ===")
        for t in sorted(by_type.keys()):
            items = by_type[t]
            preview = ", ".join(items[:10])
            more = f" (+{len(items) - 10})" if len(items) > 10 else ""
            print(f"  {t}: {len(items)} section(s) - {preview}{more}")
        print()

    if orphan_keys:
        print("=== Cles orphelines (top par section) ===")
        sorted_sections = sorted(orphan_keys.items(), key=lambda kv: -len(kv[1]))
        for name, keys in sorted_sections[:args.limit]:
            preview = ", ".join(keys[:5])
            more = f" (+{len(keys) - 5})" if len(keys) > 5 else ""
            print(f"  [{name}] {len(keys)} cle(s): {preview}{more}")
        if len(sorted_sections) > args.limit:
            print(f"  ... et {len(sorted_sections) - args.limit} autres sections")
        print()

    if args.write:
        write_cleaned(sections, args.write, reachable, orphan_keys)
        print(f"Version nettoyee ecrite: {args.write}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
