"""Anki add-on to import the Acted Flashcards CP1 deck.

The add-on bundles the original TSV file ("Acted Flashcards CP1 - incomplete.txt")
and offers a Tools menu action that imports any missing notes into a deck called
"Acted Flashcards CP1".
"""

from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path
from typing import List

from aqt import gui_hooks, mw
from aqt.qt import QAction
from aqt.utils import askUser, showInfo, showWarning

ADDON_PATH = Path(__file__).resolve().parent
DATA_PATH = ADDON_PATH / "Acted Flashcards CP1 - incomplete.txt"
DECK_NAME = "Acted Flashcards CP1"
MODEL_NAME = "Acted Flashcards CP1"


@dataclass
class Flashcard:
    front: str
    back: str


def load_flashcards() -> List[Flashcard]:
    if not DATA_PATH.exists():
        raise FileNotFoundError(f"Could not find bundled data file at {DATA_PATH}")

    flashcards: List[Flashcard] = []
    with DATA_PATH.open("r", encoding="utf-8-sig") as f:
        reader = csv.reader(f, delimiter="\t")
        for row in reader:
            if not row:
                continue
            first = row[0].strip()
            if first.startswith("#"):
                continue
            front = first
            back = row[1] if len(row) > 1 else ""
            flashcards.append(Flashcard(front=front, back=back))
    return flashcards


def ensure_model(col):
    mm = col.models
    model = mm.byName(MODEL_NAME)
    if model is None:
        model = mm.new(MODEL_NAME)
        mm.addField(model, mm.newField("Front"))
        mm.addField(model, mm.newField("Back"))
        template = mm.newTemplate("Card 1")
        template["qfmt"] = "{{Front}}"
        template["afmt"] = "{{FrontSide}}<hr id=answer>{{Back}}"
        mm.addTemplate(model, template)
        mm.add(model)
    return model


def import_flashcards() -> None:
    if mw.col is None:
        showWarning("Please open a collection before importing the flashcards.")
        return

    col = mw.col
    flashcards = load_flashcards()
    if not flashcards:
        showWarning("No flashcards were found in the bundled data file.")
        return

    if not askUser(
        f"Import {len(flashcards)} flashcards into the '{DECK_NAME}' deck?\n"
        "Existing cards with the same front text will be skipped."
    ):
        return

    deck_id = col.decks.id(DECK_NAME)
    col.decks.select(deck_id)

    model = ensure_model(col)
    col.models.setCurrent(model)

    existing_note_ids = col.find_notes(f'deck:"{DECK_NAME}"')
    existing_fronts = set()
    for nid in existing_note_ids:
        note = col.get_note(nid)
        if note.fields:
            existing_fronts.add(note.fields[0])

    added = 0
    for card in flashcards:
        if card.front in existing_fronts:
            continue
        note = col.newNote(model)
        note.fields[0] = card.front
        if len(note.fields) > 1:
            note.fields[1] = card.back
        note.tags.append("ActedFlashcardsCP1")
        col.addNote(note)
        added += 1
        existing_fronts.add(card.front)

    col.reset()
    mw.reset()

    showInfo(f"Imported {added} new flashcards into '{DECK_NAME}'.")


def on_profile_loaded() -> None:
    if mw is None:
        return

    for action in mw.form.menuTools.actions():
        if action.text() == "Import Acted Flashcards CP1":
            break
    else:
        action = QAction("Import Acted Flashcards CP1", mw)
        action.triggered.connect(import_flashcards)
        mw.form.menuTools.addAction(action)


gui_hooks.profile_did_open.append(lambda _: on_profile_loaded())
