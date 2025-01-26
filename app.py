from flask import Flask, render_template, jsonify, request
from game_logic import stworz_talie, rozdaj_karty

app = Flask(__name__)

# Globalne zmienne gry
talia = []
reka_gracza_1 = []
reka_gracza_2 = []
stos = []
aktualny_gracz = 1  # 1 oznacza Gracza 1, 2 oznacza Gracza 2
karta_dobrana = False  # Flaga oznaczająca, czy gracz dobrał już kartę w swojej turze


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/start_game")
def start_game():
    global talia, reka_gracza_1, reka_gracza_2, stos, aktualny_gracz, karta_dobrana
    talia = stworz_talie()
    reka_gracza_1, reka_gracza_2, stos = rozdaj_karty(talia)
    aktualny_gracz = 1  # Grę zaczyna Gracz 1
    karta_dobrana = False
    return jsonify({
        "reka_gracza_1": reka_gracza_1,
        "reka_gracza_2": reka_gracza_2,
        "stos": stos[-1],  # Pokazujemy wierzchnią kartę stosu
        "aktualny_gracz": aktualny_gracz
    })


@app.route("/draw_card", methods=["POST"])
def draw_card():
    global talia, reka_gracza_1, reka_gracza_2, karta_dobrana

    if karta_dobrana:
        return jsonify({"error": "Już dobrałeś kartę w tej turze!"}), 400

    if not talia:
        return jsonify({"error": "Brak kart w talii!"}), 400

    karta = talia.pop(0)  # Dobieramy pierwszą kartę z talii

    if aktualny_gracz == 1:
        reka_gracza_1.append(karta)
    else:
        reka_gracza_2.append(karta)

    karta_dobrana = True  # Flaga oznaczająca, że karta została dobrana
    return jsonify({
        "dobrana_karta": karta,
        "talia_pozostalo": len(talia)
    })


@app.route("/discard_card", methods=["POST"])
def discard_card():
    global reka_gracza_1, reka_gracza_2, stos, aktualny_gracz, karta_dobrana

    dane = request.json
    karta = dane.get("karta")

    if not karta_dobrana:
        return jsonify({"error": "Najpierw musisz dobrać kartę!"}), 400

    if aktualny_gracz == 1 and karta in reka_gracza_1:
        reka_gracza_1.remove(karta)
    elif aktualny_gracz == 2 and karta in reka_gracza_2:
        reka_gracza_2.remove(karta)
    else:
        return jsonify({"error": "Nieprawidłowa karta!"}), 400

    stos.append(karta)  # Wyrzucamy kartę na stos
    karta_dobrana = False  # Reset flagi po zakończeniu tury
    aktualny_gracz = 2 if aktualny_gracz == 1 else 1  # Zmiana kolejki

    return jsonify({
        "stos": stos[-1],  # Wierzchnia karta stosu
        "aktualny_gracz": aktualny_gracz
    })


if __name__ == "__main__":
    app.run(debug=True)
