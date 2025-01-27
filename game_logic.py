import random


def stworz_talie():
    """
    Tworzy talię złożoną z 2 zestawów kart (od 2 do 10, J, Q, K, A) oraz 2 jokerów na talię.
    """
    kolory = ["Trefl", "Karo", "Kier", "Pik"]
    wartosci = [str(i) for i in range(2, 11)] + ["J", "Q", "K", "A"]
    talia = [f"{wartosc} {kolor}" for kolor in kolory for wartosc in wartosci]
    jokery = ["Joker 1", "Joker 2"]

    # Tworzymy talię z dwóch zestawów
    pelna_talia = talia * 2 + jokery * 2
    random.shuffle(pelna_talia)  # Dokładne tasowanie talii
    return pelna_talia


def rozdaj_karty(talia, liczba_kart=14):
    """
    Rozdaje karty graczowi i drugiemu graczowi, pozostawia resztę jako stos.
    """
    reka_gracza_1 = talia[:liczba_kart]
    reka_gracza_2 = talia[liczba_kart:liczba_kart * 2]
    pozostale_karty = talia[liczba_kart * 2:]
    return reka_gracza_1, reka_gracza_2, pozostale_karty


def punktacja_karty(karta):
    """
    Zwraca wartość punktową dla danej karty.
    """
    wartosc = karta.split()[0]

    if wartosc.isdigit():  # Jeśli to liczba (2–10)
        return int(wartosc)
    elif wartosc in ["J", "Q", "K"]:
        return 10
    elif wartosc in ["A", "Joker"]:
        return 0
    return 0
