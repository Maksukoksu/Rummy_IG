import random
import itertools

# Licznik do unikalnych ID kart
card_id_counter = itertools.count(1)

def generate_card_obj(name):
    """
    Tworzy obiekt karty z unikalnym ID i nazwą, np. {"id":1, "name":"5 Kier"}.
    """
    new_id = next(card_id_counter)
    return {"id": new_id, "name": name}

def stworz_talie():
    """
    Tworzy kompletną talię z ID:
      - 2×(2..10, J, Q, K, A) w 4 kolorach,
      - 2×(Joker 1, Joker 2).
    Miesza całość.
    """
    kolory = ["Trefl", "Karo", "Kier", "Pik"]
    wartosci = [str(i) for i in range(2, 11)] + ["J", "Q", "K", "A"]

    single_set = [f"{w} {k}" for w in wartosci for k in kolory]
    jokers = ["Joker 1", "Joker 2"]

    # 2 zestawy + 2× jokers
    nazwy = single_set*2 + jokers*2
    random.shuffle(nazwy)

    # Zamieniamy stringi na obiekty z unikalnym ID
    return [generate_card_obj(n) for n in nazwy]


def rozdaj_karty(talia, liczba=14):
    """
    Rozdaje: gracz1->14, gracz2->14, reszta -> 'talia'.
    Zwraca (reka1, reka2, pozostale).
    """
    r1 = talia[:liczba]
    r2 = talia[liczba:2*liczba]
    reszta = talia[2*liczba:]
    return r1, r2, reszta

def punktacja_karty(k):
    """
    Oblicza punkty wg name, np. "10 Kier" -> 10, "Joker" -> 0,
    "J/Q/K/A" -> 10 (lub 0 w zależności od zasad).
    """
    name = k["name"]
    first = name.split()[0]
    if first.isdigit():
        return int(first)
    if first in ["J","Q","K","A"]:
        return 10
    if first.startswith("Joker"):
        return 0
    return 0

# -------------------------------------------------
#   Funkcje sprawdzające SET i SEKWENCJĘ (z Jokerami)
# -------------------------------------------------

def is_set(karty):
    """
    Sprawdza, czy 'karty' tworzy SET (3–4 karty tej samej wartości, różne kolory).
    Joker może być w tych kartach (rozszerzona logika dozwolona).
    Tu w najprostszej wersji - jeśli w normalnych kartach
    jest 1 wartość i kolory się nie powtarzają, to ok.
    """
    if len(karty) < 3 or len(karty) > 4:
        return False

    jokers = [c for c in karty if c["name"].startswith("Joker")]
    normal = [c for c in karty if not c["name"].startswith("Joker")]
    if not normal:
        # same jokery => teoretycznie może być set 3–4 Jokerów
        return len(karty) <= 4 and len(karty) >= 3

    # Sprawdź wartość
    valset = { c["name"].split()[0] for c in normal }
    if len(valset) != 1:
        return False
    # Kolory
    colors = [ c["name"].split()[1] for c in normal ]
    if len(set(colors)) != len(colors):
        return False

    # Max 4 karty w sumie
    if len(karty) > 4:
        return False

    return True


def is_sequence(karty):
    """
    Sprawdza, czy 'karty' (lista obiektów) tworzy SEKWENCJĘ
    z obsługą Jokerów (wypełnianie luk wewnątrz i wydłużanie na końcach).
    Warunki:
      - >= 3 karty
      - normalne karty w 1 kolorze
      - brak duplikatów wartości
      - luki wypełniane przez Jokery
    """
    if len(karty) < 3:
        return False

    jokers = [c for c in karty if c["name"].startswith("Joker")]
    normal = [c for c in karty if not c["name"].startswith("Joker")]
    jokers_count = len(jokers)

    if not normal:
        # same jokery => np. 3 jokery -> teoretycznie sekwencja
        return len(karty) >= 3

    # Sprawdzamy kolor
    splitted = [c["name"].split() for c in normal]  # np. [["5","Kier"], ["7","Kier"]]
    col = [sp[1] for sp in splitted]
    if len(set(col)) != 1:
        return False

    # Konwersja wartości na int
    valmap = {"J":11, "Q":12, "K":13, "A":14}
    nums = []
    for c in normal:
        first = c["name"].split()[0]
        if first.isdigit():
            nums.append(int(first))
        else:
            nums.append(valmap.get(first,0))
    nums.sort()

    # Duplikaty -> fail
    for i in range(len(nums)-1):
        if nums[i] == nums[i+1]:
            return False

    min_v = nums[0]
    max_v = nums[-1]

    # Liczymy luki wewnętrzne
    needed = 0
    for i in range(len(nums)-1):
        gap = nums[i+1] - nums[i] -1
        if gap < 0:
            return False
        needed += gap

    if needed > jokers_count:
        return False
    # wypełniamy luki
    jokers_left = jokers_count - needed

    # Liczba wartości w spójnym bloku min..max
    block_len = max_v - min_v + 1
    final_len = block_len + jokers_left

    return final_len >= 3

# -------------------------------------------------
#   Backtracking do tworzenia grup (sety/sekwencje)
# -------------------------------------------------

def znajdz_grupowanie(karty):
    """
    Próbuje rozłożyć listę obiektów karty (id,name)
    na poprawne sety lub sekwencje (z Jokerami).
    Zwraca (True, total_points, [lista_grup]) lub (False,0,None).
    """
    solution = backtrack_groups(karty)
    if solution is None:
        return (False, 0, None)
    else:
        total = sum(punktacja_karty(c) for group in solution for c in group)
        return (True, total, solution)

def backtrack_groups(cards):
    if not cards:
        return []

    n = len(cards)
    import itertools

    # Spróbujmy *dowolnej* podgrupy 3..n
    for size in range(3, n+1):
        for combo in itertools.combinations(range(n), size):
            group = [cards[i] for i in combo]
            if is_set(group) or is_sequence(group):
                leftover = remove_by_indexes(cards, combo)
                sub = backtrack_groups(leftover)
                if sub is not None:
                    return [group] + sub
    return None

def remove_by_indexes(cards, idxs):
    s = set(idxs)
    return [c for i,c in enumerate(cards) if i not in s]
def sort_group_for_display(group):
    """
    Sortuje karty w grupie rosnąco po wartości.
    Jokery (np. 'Joker 1') wrzucamy na koniec (key=99).
    """
    valmap = {"J":11, "Q":12, "K":13, "A":14}
    def card_value(c):
        n = c["name"].split()[0]
        if n.startswith("Joker"):
            return 99
        if n.isdigit():
            return int(n)
        return valmap.get(n,0)

    # Ewentualnie można też sortować po kolorze, jeśli chcesz.
    return sorted(group, key=card_value)
