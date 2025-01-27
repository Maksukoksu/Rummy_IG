from flask import Flask, render_template, jsonify, request
from game_logic import stworz_talie, rozdaj_karty, punktacja_karty

app = Flask(__name__)

# Globalne zmienne gry
talia = []
reka_gracza_1 = []
reka_gracza_2 = []
stos = []  # Stos kart wyrzuconych
aktualny_gracz = 1
karta_dobrana = False


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/start_game")
def start_game():
    global talia, reka_gracza_1, reka_gracza_2, stos, aktualny_gracz, karta_dobrana
    talia = stworz_talie()
    reka_gracza_1, reka_gracza_2, stos = rozdaj_karty(talia)
    aktualny_gracz = 1
    karta_dobrana = False
    stos = []  # Resetujemy stos kart wyrzuconych
    return jsonify({
        "reka_gracza_1": reka_gracza_1,
        "punkty_gracza_1": sum(punktacja_karty(karta) for karta in reka_gracza_1),
        "reka_gracza_2": reka_gracza_2,
        "punkty_gracza_2": sum(punktacja_karty(karta) for karta in reka_gracza_2),
        "stos": None,  # Brak wyrzuconych kart na początku
        "aktualny_gracz": aktualny_gracz
    })


@app.route("/draw_card", methods=["POST"])
def draw_card():
    global talia, reka_gracza_1, reka_gracza_2, karta_dobrana

    if karta_dobrana:
        return jsonify({"error": "Już dobrałeś kartę w tej turze!"}), 400

    if not talia:
        return jsonify({"error": "Brak kart w talii!"}), 400

    # Losowe dobieranie karty z talii
    import random
    index = random.randint(0, len(talia) - 1)
    karta = talia.pop(index)

    if aktualny_gracz == 1:
        reka_gracza_1.append(karta)
    else:
        reka_gracza_2.append(karta)

    karta_dobrana = True
    return jsonify({
        "dobrana_karta": karta,
        "talia_pozostalo": len(talia)
    })



@app.route("/discard_card", methods=["POST"])
def discard_card():
    global reka_gracza_1, reka_gracza_2, stos, aktualny_gracz, karta_dobrana

    dane = request.json
    karta_index = dane.get("karta_index")  # Otrzymujemy indeks wyrzucanej karty

    if not karta_dobrana:
        return jsonify({"error": "Najpierw musisz dobrać kartę!"}), 400

    if aktualny_gracz == 1 and karta_index < len(reka_gracza_1):
        wyrzucana_karta = reka_gracza_1.pop(karta_index)
    elif aktualny_gracz == 2 and karta_index < len(reka_gracza_2):
        wyrzucana_karta = reka_gracza_2.pop(karta_index)
    else:
        return jsonify({"error": "Nieprawidłowa karta!"}), 400

    stos.append(wyrzucana_karta)  # Dodajemy kartę na stos
    karta_dobrana = False
    aktualny_gracz = 2 if aktualny_gracz == 1 else 1

    return jsonify({
        "stos": stos[-1],  # Ostatnia karta na stosie
        "aktualny_gracz": aktualny_gracz,
        "punkty_gracza_1": sum(punktacja_karty(karta) for karta in reka_gracza_1),
        "punkty_gracza_2": sum(punktacja_karty(karta) for karta in reka_gracza_2)
    })


if __name__ == "__main__":
    app.run(debug=True)
