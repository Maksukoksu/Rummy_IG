from flask import Flask, render_template, request, jsonify
from game_logic import (
    stworz_talie, punktacja_karty, rozdaj_karty,
    is_set, is_sequence, znajdz_grupowanie, sort_group_for_display
)

app = Flask(__name__)

# Proste globalne zmienne do jednej gry (2–4 graczy):
num_players = 2
players_hands = []
talia = []
stos = []
cards_on_table = []
current_player_index = 0
karta_dobrana = False

# Tablica informująca, czy gracz i (0-based) już wyłożył co najmniej 51 pkt
players_has_51 = []

@app.route("/")
def show_index():
    return render_template("index.html")

@app.route("/setup_game", methods=["POST"])
def setup_game():
    global num_players, players_hands, talia, stos, cards_on_table
    global current_player_index, karta_dobrana, players_has_51

    data = request.json
    if not data:
        return jsonify({"error": "Brak JSON"}), 400
    num = data.get("numPlayers")
    if not isinstance(num, int) or num < 2 or num > 4:
        return jsonify({"error": "Niepoprawna liczba graczy (2–4)"}), 400

    # Tworzymy stan gry
    num_players = num
    players_hands.clear()
    stos.clear()
    cards_on_table.clear()
    current_player_index = 0
    karta_dobrana = False
    # Każdy gracz na początku nie ma jeszcze 51 punktów wyłożonych:
    players_has_51 = [False]*num_players

    # Generujemy talię i rozdajemy
    full_deck = stworz_talie()
    hands, leftover = rozdaj_karty(full_deck, n_players=num_players, liczba=14)
    for h in hands:
        players_hands.append(h)
    talia[:] = leftover

    # Prosty "game_id" – w tym przykładzie zawsze =1
    return jsonify({"redirect_url": "/game?game_id=1"})

@app.route("/game")
def show_game():
    return render_template("game.html")

@app.route("/get_game_state")
def get_game_state():
    # W tym demie mamy tylko jedną grę => id=1
    game_id = request.args.get("game_id")
    data = {
        "numPlayers": num_players,
        "playersHands": players_hands,
        "currentPlayerIndex": current_player_index,
        "cardsOnTable": cards_on_table,
        "lastDiscarded": stos[-1] if stos else None
    }
    return jsonify(data)

@app.route("/draw_card", methods=["POST"])
def draw_card():
    global current_player_index, karta_dobrana
    pIndex = request.args.get("playerIndex")
    if pIndex is None:
        return jsonify({"error":"Brak playerIndex"}),400
    pIndex = int(pIndex)
    if pIndex != current_player_index:
        return jsonify({"error":"Nie Twój ruch!"}), 400

    if karta_dobrana:
        return jsonify({"error":"Już dobrałeś kartę w tej turze!"}), 400
    if not talia:
        return jsonify({"error":"Brak kart w talii!"}), 400

    card = talia.pop()
    players_hands[pIndex].append(card)
    karta_dobrana = True

    return jsonify({"dobrana_karta": card})

@app.route("/lay_down_selected", methods=["POST"])
def lay_down_selected():
    global current_player_index, karta_dobrana, cards_on_table, players_has_51

    data = request.json
    pIndex = data.get("playerIndex")
    cards_ids = data.get("cards_ids")
    if pIndex is None or cards_ids is None:
        return jsonify({"error":"Brak playerIndex lub cards_ids!"}), 400
    pIndex = int(pIndex)
    if pIndex != current_player_index:
        return jsonify({"error":"Nie Twój ruch!"}), 400

    if not karta_dobrana:
        return jsonify({"error":"Najpierw musisz dobrać kartę!"}), 400

    reka = players_hands[pIndex]
    selected = []
    for cid in cards_ids:
        idx = next((i for i,c in enumerate(reka) if c["id"] == cid), None)
        if idx is None:
            return jsonify({"error":f"Karta {cid} nie w ręce."}), 400
        selected.append(reka[idx])

    valid, total_points, groups = znajdz_grupowanie(selected)
    if not valid:
        return jsonify({"error":"Niepoprawne sety/sekwencje."}), 400

    # --- Wymóg 51 pkt przy PIERWSZYM wyłożeniu ---
    if not players_has_51[pIndex] and total_points < 51:
        return jsonify({
            "error": f"Pierwsze wyłożenie musi mieć co najmniej 51 pkt (masz {total_points})."
        }), 400

    # Usuwamy te karty z ręki
    for cid in cards_ids:
        i2 = next((i for i,c in enumerate(reka) if c["id"] == cid), None)
        if i2 is not None:
            reka.pop(i2)

    # Dodajemy grupy do cards_on_table (po sortowaniu)
    for g in groups:
        g_sorted = sort_group_for_display(g)
        cards_on_table.append(g_sorted)

    # Jeśli to pierwsze wyłożenie i >=51 => ustalamy flagę
    if not players_has_51[pIndex] and total_points >= 51:
        players_has_51[pIndex] = True

    return jsonify({
        "newHand": reka,
        "cardsOnTable": cards_on_table
    })

@app.route("/discard_card", methods=["POST"])
def discard_card():
    global current_player_index, karta_dobrana

    data = request.json
    pIndex = data.get("playerIndex")
    card_id = data.get("card_id")
    if pIndex is None or card_id is None:
        return jsonify({"error":"Brak playerIndex lub card_id"}),400
    pIndex = int(pIndex)
    if pIndex != current_player_index:
        return jsonify({"error":"Nie Twój ruch!"}),400

    if not karta_dobrana:
        return jsonify({"error":"Najpierw musisz dobrać kartę!"}),400

    reka = players_hands[pIndex]
    idx = next((i for i,c in enumerate(reka) if c["id"] == card_id), None)
    if idx is None:
        return jsonify({"error":"Nie masz tej karty"}),400

    wyrzucana = reka.pop(idx)
    stos.append(wyrzucana)
    karta_dobrana = False

    if len(reka) == 0:
        return end_game(pIndex)

    # Zmiana gracza
    current_player_index = (current_player_index + 1) % num_players

    return jsonify({
        "newHand": reka,
        "nextPlayerIndex": current_player_index,
        "lastDiscardedCard": wyrzucana
    })

def end_game(wIndex):
    # prosty: sumujemy karty pozostałe w innych rękach
    total_penalty = 0
    for i,hand in enumerate(players_hands):
        if i != wIndex:
            total_penalty += sum(punktacja_karty(c) for c in hand)

    return jsonify({
        "info": f"Gracz {wIndex+1} wyrzucił ostatnią kartę i wygrywa!",
        "punkty_przegranego": total_penalty,
        "game_over": True,
        "winnerIndex": wIndex
    })

# -------------------------
#  Endpoint do dołożenia kart do grupy
# -------------------------
@app.route("/add_to_table", methods=["POST"])
def add_to_table():
    global cards_on_table, players_hands
    global current_player_index, players_has_51

    data = request.json
    if not data:
        return jsonify({"error":"Brak JSON"}),400

    pIndex = data.get("playerIndex")
    group_index = data.get("group_index")
    cards_ids = data.get("cards_ids")

    if pIndex is None or group_index is None or cards_ids is None:
        return jsonify({"error":"Brak playerIndex/group_index/cards_ids"}),400

    pIndex = int(pIndex)
    group_index = int(group_index)

    # Sprawdzamy, czy to aktualny gracz
    if pIndex != current_player_index:
        return jsonify({"error":"Nie Twój ruch!"}),400

    # Wymagamy, by gracz miał >=51 (bo dokłada dopiero po 1. wyłożeniu)
    if not players_has_51[pIndex]:
        return jsonify({"error":"Najpierw musisz mieć wyłożone 51 pkt, by dokładać!"}),400

    # Walidujemy index grupy
    if group_index<0 or group_index>=len(cards_on_table):
        return jsonify({"error":"Nieprawidłowy index grupy!"}),400

    # Pobieramy oryginalną grupę
    original_group = cards_on_table[group_index]

    # Kopiujemy
    import copy
    new_group = copy.deepcopy(original_group)

    # Zbieramy karty z ręki
    reka = players_hands[pIndex]
    added_cards = []
    for cid in cards_ids:
        idx = next((i for i,c in enumerate(reka) if c["id"]==cid), None)
        if idx is None:
            return jsonify({"error": f"Karta {cid} nie należy do Twojej ręki"}),400
        added_cards.append(reka[idx])

    # Dołączamy karty do new_group
    new_group.extend(added_cards)

    # Sprawdzamy, czy oryginalna grupa była setem, czy sekwencją
    was_set = is_set(original_group)
    was_seq = is_sequence(original_group)

    # Po dołożeniu – wciąż musi być set/sekwencja
    if was_set and not is_set(new_group):
        return jsonify({"error": "Po dołożeniu grupa przestała być setem!"}),400
    if was_seq and not is_sequence(new_group):
        return jsonify({"error": "Po dołożeniu grupa przestała być sekwencją!"}),400

    # Jeśli OK => usuwamy karty z ręki
    for cid in cards_ids:
        i2 = next((i for i,c in enumerate(reka) if c["id"] == cid), None)
        if i2 is not None:
            reka.pop(i2)

    # Możemy posortować sekwencję
    if was_seq:
        new_group = sort_group_for_display(new_group)

    # Podmieniamy grupę
    cards_on_table[group_index] = new_group

    return jsonify({
        "success": True,
        "new_hand": reka,
        "cards_on_table": cards_on_table
    })


@app.route("/update_hand_order", methods=["POST"])
def update_hand_order():
    global num_players, players_hands

    game_id = request.args.get("game_id")
    pIndex = request.args.get("playerIndex")
    if pIndex is None:
        return jsonify({"error": "Brak playerIndex"}), 400
    pIndex = int(pIndex)

    data = request.json
    if not data:
        return jsonify({"error": "Brak JSON"}), 400

    new_order_ids = data.get("new_order_ids")
    if not new_order_ids or not isinstance(new_order_ids, list):
        return jsonify({"error": "Niepoprawna lista new_order_ids"}), 400

    if pIndex < 0 or pIndex >= num_players:
        return jsonify({"error":"Nieprawidłowy indeks gracza"}), 400

    hand = players_hands[pIndex]

    # Odtwarzamy nową rękę na podstawie kolejności ID
    id_to_card = { c["id"]: c for c in hand }
    new_hand = []
    for cid in new_order_ids:
        card_obj = id_to_card.get(cid)
        if not card_obj:
            return jsonify({"error": f"Karta {cid} nie należy do ręki gracza"}),400
        new_hand.append(card_obj)

    players_hands[pIndex] = new_hand

    return jsonify({"success": True})


if __name__=="__main__":
    app.run(debug=True)
