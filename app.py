from flask import Flask, render_template, jsonify, request
from game_logic import (
    stworz_talie,
    rozdaj_karty,
    punktacja_karty,
    znajdz_grupowanie,
    sort_group_for_display
)

app = Flask(__name__)

talia = []
reka_gracza_1 = []
reka_gracza_2 = []
stos = []
cards_on_table = []

aktualny_gracz = 1
karta_dobrana = False

gracz1_wylozyl_51 = False
gracz2_wylozyl_51 = False


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/start_game")
def start_game():
    global talia, reka_gracza_1, reka_gracza_2, stos, cards_on_table
    global aktualny_gracz, karta_dobrana
    global gracz1_wylozyl_51, gracz2_wylozyl_51

    pelna = stworz_talie()
    r1, r2, pozostale = rozdaj_karty(pelna, 14)
    talia[:] = pozostale
    reka_gracza_1[:] = r1
    reka_gracza_2[:] = r2
    stos.clear()
    cards_on_table.clear()

    aktualny_gracz = 1
    karta_dobrana = False
    gracz1_wylozyl_51 = False
    gracz2_wylozyl_51 = False

    return jsonify({
        "reka_gracza_1": reka_gracza_1,
        "reka_gracza_2": reka_gracza_2,
        "stos": None,
        "aktualny_gracz": aktualny_gracz
    })


@app.route("/draw_card", methods=["POST"])
def draw_card():
    global talia, aktualny_gracz, karta_dobrana

    if karta_dobrana:
        return jsonify({"error": "W tej turze już dobrałeś kartę!"}), 400
    if not talia:
        return jsonify({"error": "Brak kart w talii!"}), 400

    card = talia.pop()
    if aktualny_gracz == 1:
        reka_gracza_1.append(card)
    else:
        reka_gracza_2.append(card)

    karta_dobrana = True
    return jsonify({
        "dobrana_karta": card,
        "talia_pozostalo": len(talia)
    })


@app.route("/lay_down_selected", methods=["POST"])
def lay_down_selected():
    global aktualny_gracz, karta_dobrana
    global gracz1_wylozyl_51, gracz2_wylozyl_51
    global cards_on_table

    if not karta_dobrana:
        return jsonify({"error": "Najpierw musisz dobrać kartę w tej turze!"}), 400

    data = request.json
    cards_ids = data.get("cards_ids")
    if not cards_ids or not isinstance(cards_ids, list):
        return jsonify({"error": "Brak poprawnej listy 'cards_ids'"}), 400

    if aktualny_gracz == 1:
        reka = reka_gracza_1
        juz_51 = gracz1_wylozyl_51
    else:
        reka = reka_gracza_2
        juz_51 = gracz2_wylozyl_51

    # Znajdujemy obiekty wg ID
    selected_cards = []
    for cid in cards_ids:
        idx = next((i for i,c in enumerate(reka) if c["id"] == cid), None)
        if idx is None:
            return jsonify({"error": f"Karta ID={cid} nie znaleziona w ręce."}), 400
        selected_cards.append(reka[idx])

    # sprawdzamy sety/sekwencje
    valid, total_points, groups = znajdz_grupowanie(selected_cards)
    if not valid:
        return jsonify({"error": "Wybrane karty nie tworzą poprawnych setów/sekwencji"}), 400

    if not juz_51 and total_points < 51:
        return jsonify({"error": f"Pierwsze wyłożenie musi mieć co najmniej 51 pkt (masz {total_points})"}), 400

    # Usuwamy te karty z ręki
    for cid in cards_ids:
        i2 = next((i for i,c in enumerate(reka) if c["id"] == cid), None)
        if i2 is not None:
            reka.pop(i2)

    # Dodajemy grupy do global cards_on_table, ALE sortujemy do ładnego wyświetlenia
    from game_logic import sort_group_for_display
    for g in groups:
        sorted_g = sort_group_for_display(g)
        cards_on_table.append(sorted_g)

    # Ustawiamy flagę 51 jeśli osiągnięte
    if aktualny_gracz == 1 and not gracz1_wylozyl_51 and total_points >= 51:
        gracz1_wylozyl_51 = True
    elif aktualny_gracz == 2 and not gracz2_wylozyl_51 and total_points >= 51:
        gracz2_wylozyl_51 = True

    return jsonify({
        "success": True,
        "new_hand": reka,
        "cards_on_table": cards_on_table
    })


@app.route("/discard_card", methods=["POST"])
def discard_card():
    global aktualny_gracz, karta_dobrana, stos

    if not karta_dobrana:
        return jsonify({"error": "Najpierw musisz dobrać kartę w tej turze!"}), 400

    data = request.json
    card_id = data.get("card_id")
    if card_id is None:
        return jsonify({"error": "Brak 'card_id' do wyrzucenia"}), 400

    if aktualny_gracz == 1:
        idx = next((i for i,c in enumerate(reka_gracza_1) if c["id"] == card_id), None)
        if idx is None:
            return jsonify({"error": f"Karta id={card_id} nie znaleziona w ręce gracza1"}), 400
        wyrzucana = reka_gracza_1.pop(idx)
    else:
        idx = next((i for i,c in enumerate(reka_gracza_2) if c["id"] == card_id), None)
        if idx is None:
            return jsonify({"error": f"Karta id={card_id} nie znaleziona w ręce gracza2"}), 400
        wyrzucana = reka_gracza_2.pop(idx)

    stos.append(wyrzucana)
    karta_dobrana = False

    # Sprawdzamy, czy gracz wyrzucił ostatnią kartę
    if aktualny_gracz == 1 and len(reka_gracza_1) == 0:
        return koniec_gry(1)
    elif aktualny_gracz == 2 and len(reka_gracza_2) == 0:
        return koniec_gry(2)

    aktualny_gracz = 2 if aktualny_gracz == 1 else 1

    return jsonify({
        "stos": wyrzucana,
        "aktualny_gracz": aktualny_gracz
    })


def koniec_gry(gracz):
    """
    Ktoś wyrzucił ostatnią kartę => koniec gry.
    Dodajemy punkty przegranego = sum(kart w ręce).
    """
    if gracz == 1:
        pkt_przegranego = sum(punktacja_karty(c) for c in reka_gracza_2)
    else:
        pkt_przegranego = sum(punktacja_karty(c) for c in reka_gracza_1)

    return jsonify({
        "info": f"Gracz {gracz} wyrzucił ostatnią kartę i wygrywa!",
        "punkty_przegranego": pkt_przegranego,
        "game_over": True
    })

@app.route("/add_to_table", methods=["POST"])
def add_to_table():
    """
    JSON body:
    {
      "group_index": 0,
      "cards_ids": [123, 456]
    }
    1. Sprawdzamy, czy aktualny gracz jest "wyłożony" (graczX_wylozyl_51).
    2. Pobieramy grupę z cards_on_table[group_index].
    3. Sprawdzamy, czy to set czy sekwencja.
    4. Dodajemy do niej karty z ręki (po ID).
    5. Sprawdzamy, czy wciąż jest set/sekwencja.
       Jeśli tak, zapisujemy.
       Jeśli nie -> błąd 400.
    6. Zwracamy nową rękę i cards_on_table w JSON.
    """
    global aktualny_gracz, cards_on_table

    # 1. Czy gracz już wyłożył 51?
    if aktualny_gracz == 1:
        if not gracz1_wylozyl_51:
            return jsonify({"error": "Musisz najpierw wyłożyć 51 punktów, aby móc dokładać do stołu."}), 400
        reka = reka_gracza_1
    else:
        if not gracz2_wylozyl_51:
            return jsonify({"error": "Musisz najpierw wyłożyć 51 punktów, aby móc dokładać do stołu."}), 400
        reka = reka_gracza_2

    data = request.json
    group_index = data.get("group_index")
    cards_ids = data.get("cards_ids", [])

    # Walidacja
    if group_index is None or group_index < 0 or group_index >= len(cards_on_table):
        return jsonify({"error": "Nieprawidłowy indeks grupy na stole."}), 400
    if not cards_ids:
        return jsonify({"error": "Brak cards_ids albo pusta lista."}), 400

    # 2. Pobieramy istniejącą grupę
    original_group = cards_on_table[group_index]
    # Kopiujemy tę grupę, żeby w razie błędu łatwo przywrócić
    import copy
    new_group = copy.deepcopy(original_group)

    # 3. Sprawdzamy, czy to set czy sekwencja
    from game_logic import is_set, is_sequence

    was_set = is_set(original_group)
    was_seq = is_sequence(original_group)
    if not (was_set or was_seq):
        return jsonify({"error": "Aktualna grupa na stole nie jest setem ani sekwencją? Błąd stanu."}), 400

    # 4. Pobieramy karty z ręki
    added_cards = []
    for cid in cards_ids:
        idx = next((i for i,c in enumerate(reka) if c["id"] == cid), None)
        if idx is None:
            return jsonify({"error": f"Karta o ID={cid} nie znaleziona w ręce."}), 400
        added_cards.append(reka[idx])

    # 5. Dodajemy do new_group
    new_group.extend(added_cards)

    # 6. Sprawdzamy, czy wciąż jest ten sam typ (lub w Remiku można by zaakceptować,
    #    że set staje się sekwencją; ale to raczej nielogiczne – przy prostych zasadach
    #    lepiej trzymać się jednego typu).
    if was_set and not is_set(new_group):
        return jsonify({"error": "Po dołożeniu kart ta grupa nie jest już poprawnym setem."}), 400
    if was_seq and not is_sequence(new_group):
        return jsonify({"error": "Po dołożeniu kart ta grupa nie jest już poprawną sekwencją."}), 400

    # 7. Jeśli ok -> usuwamy karty z ręki i aktualizujemy group na stole
    for cid in cards_ids:
        i2 = next((i for i,c in enumerate(reka) if c["id"] == cid), None)
        if i2 is not None:
            reka.pop(i2)

    # Zastępujemy w cards_on_table
    # Dla czytelności możesz też sortować, jeśli to sekwencja:
    if was_seq:
        from game_logic import sort_group_for_display
        new_group = sort_group_for_display(new_group)

    cards_on_table[group_index] = new_group

    return jsonify({
        "success": True,
        "new_hand": reka,
        "cards_on_table": cards_on_table
    })

if __name__ == "__main__":
    app.run(debug=True)
