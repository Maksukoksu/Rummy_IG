from flask import Flask, render_template, request, jsonify
from game_logic import stworz_talie, punktacja_karty, rozdaj_karty, is_set, is_sequence, znajdz_grupowanie, sort_group_for_display

app = Flask(__name__)

# Proste globalne zmienne do jednej gry:
num_players = 2
players_hands = []
talia = []
stos = []
cards_on_table = []
current_player_index = 0
karta_dobrana = False

players_has_51 = []

@app.route("/")
def show_index():
    # Zwraca index.html (strona startowa)
    return render_template("index.html")

@app.route("/setup_game", methods=["POST"])
def setup_game():
    global num_players, players_hands, talia, stos, cards_on_table
    global current_player_index, karta_dobrana, players_has_51

    data = request.json
    if not data:
        return jsonify({"error":"Brak JSON"}),400
    num = data.get("numPlayers")
    if not isinstance(num, int) or num<2 or num>4:
        return jsonify({"error":"Niepoprawna liczba graczy (2–4)"}),400

    # Tworzymy stan gry
    num_players = num
    players_hands.clear()
    stos.clear()
    cards_on_table.clear()
    current_player_index = 0
    karta_dobrana = False
    players_has_51 = [False]*num_players

    # Generujemy talię i rozdajemy
    full_deck = stworz_talie()
    hands, leftover = rozdaj_karty(full_deck, n_players=num_players, liczba=14)
    for h in hands:
        players_hands.append(h)
    talia[:] = leftover

    # Prosty "game_id" – w tym demo zawsze =1
    game_id = 1
    # Zwracamy URL do /game?game_id=1
    return jsonify({"redirect_url": f"/game?game_id={game_id}"})

@app.route("/game")
def show_game():
    # Zwraca game.html (strona rozgrywki)
    return render_template("game.html")

@app.route("/get_game_state")
def get_game_state():
    game_id = request.args.get("game_id")
    # Zakładamy, że jedyna gra ma id=1. Można by sprawdzać, czy game_id=="1".
    # Budujemy JSON z info
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
    if pIndex!=current_player_index:
        return jsonify({"error":"Nie Twój ruch!"}),400

    if karta_dobrana:
        return jsonify({"error":"Już dobrałeś kartę"}),400
    if not talia:
        return jsonify({"error":"Brak kart w talii!"}),400

    card = talia.pop()
    players_hands[pIndex].append(card)
    karta_dobrana = True

    return jsonify({"dobrana_karta": card})

@app.route("/lay_down_selected", methods=["POST"])
def lay_down_selected():
    global current_player_index, karta_dobrana, cards_on_table

    data = request.json
    pIndex = data.get("playerIndex")
    cards_ids = data.get("cards_ids")
    if pIndex is None or cards_ids is None:
        return jsonify({"error":"Brak playerIndex lub cards_ids!"}),400
    pIndex = int(pIndex)
    if pIndex!=current_player_index:
        return jsonify({"error":"Nie Twój ruch!"}),400

    if not karta_dobrana:
        return jsonify({"error":"Najpierw dobierz kartę!"}),400

    reka = players_hands[pIndex]
    selected = []
    for cid in cards_ids:
        idx = next((i for i,c in enumerate(reka) if c["id"]==cid), None)
        if idx is None:
            return jsonify({"error":f"Karta {cid} nie w ręce."}),400
        selected.append(reka[idx])

    valid, total_points, groups = znajdz_grupowanie(selected)
    # Dla uproszczenia pomijamy 51-punktowe reguły
    if not valid:
        return jsonify({"error":"Niepoprawne sety/sekwencje."}),400

    # Usuwamy z ręki
    for cid in cards_ids:
        i2 = next((i for i,c in enumerate(reka) if c["id"]==cid), None)
        if i2 is not None:
            reka.pop(i2)

    # Dodajemy do stołu
    for g in groups:
        g_sorted = sort_group_for_display(g)
        cards_on_table.append(g_sorted)

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
    if pIndex!=current_player_index:
        return jsonify({"error":"Nie Twój ruch!"}),400

    if not karta_dobrana:
        return jsonify({"error":"Najpierw dobierz kartę!"}),400

    reka = players_hands[pIndex]
    idx = next((i for i,c in enumerate(reka) if c["id"]==card_id), None)
    if idx is None:
        return jsonify({"error":"Nie masz tej karty"}),400

    wyrzucana = reka.pop(idx)
    stos.append(wyrzucana)
    karta_dobrana = False

    # Sprawdzamy koniec
    if len(reka)==0:
        return end_game(pIndex)

    # Zmiana gracza
    old = current_player_index
    current_player_index = (current_player_index+1) % num_players

    return jsonify({
        "newHand": reka,
        "nextPlayerIndex": current_player_index,
        "lastDiscardedCard": wyrzucana
    })

def end_game(wIndex):
    # prosty: sumujemy karty pozostałe w innych rękach
    total_penalty = 0
    for i,hand in enumerate(players_hands):
        if i!=wIndex:
            total_penalty += sum(punktacja_karty(c) for c in hand)

    return jsonify({
        "info": f"Gracz {wIndex+1} wyrzucił ostatnią kartę i wygrywa!",
        "punkty_przegranego": total_penalty,
        "game_over": True
    })

if __name__=="__main__":
    app.run(debug=True)
