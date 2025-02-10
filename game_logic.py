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
    nazwy = single_set * 2 + jokers * 2
    random.shuffle(nazwy)

    # Zamieniamy stringi na obiekty z unikalnym ID
    return [generate_card_obj(n) for n in nazwy]


def rozdaj_karty(talia, n_players=2, liczba=14):
    """
    Rozdaje karty wielu graczom.
    Zwraca (hands, leftover), gdzie:
      - hands: lista list, np. [ [k0,k1,..], [k0,k1,..], ... ] dla n graczy
      - leftover: reszta talii
    Domyślnie n_players=2, liczba=14 kart na gracza.
    """
    offset = 0
    all_hands = []
    for i in range(n_players):
        start = offset
        end = offset + liczba
        rec = talia[start:end]
        all_hands.append(rec)
        offset += liczba

    leftover = talia[offset:]
    return all_hands, leftover


def punktacja_karty(k):
    """
    Prosta funkcja liczenia punktów "starym sposobem":
      - Cyfra => tyle
      - J/Q/K/A => 10
      - Joker => 0
    Do wykorzystania np. przy sumowaniu kart w ręce przegranego,
    lub innych celach. Nie uwzględnia As=1 wariantu.
    """
    name = k["name"]
    first = name.split()[0]
    if first.isdigit():
        return int(first)
    if first in ["J", "Q", "K", "A"]:
        return 10
    if first.startswith("Joker"):
        return 0
    return 0


# -------------------------------------------------
#   Funkcje sprawdzające SET i SEKWENCJĘ (z Jokerami)
# -------------------------------------------------

def is_set(karty):
    """
    Sprawdza, czy 'karty' (lista obiektów) tworzy SET (3–4 karty tej samej wartości,
    różne kolory). Joker może zastępować brakującą kartę wartości.
    """
    if len(karty) < 3 or len(karty) > 4:
        return False

    jokers = [c for c in karty if c["name"].startswith("Joker")]
    normal = [c for c in karty if not c["name"].startswith("Joker")]

    if not normal:
        # same jokery => np. 3–4 => set
        return 3 <= len(karty) <= 4

    # Sprawdzamy, czy normalne karty mają 1 wartość
    vals = {c["name"].split()[0] for c in normal}
    if len(vals) != 1:
        return False

    # Kolory muszą się różnić
    colors = [c["name"].split()[1] for c in normal]
    if len(set(colors)) != len(colors):
        return False

    if len(karty) > 4:
        return False

    return True


def is_sequence(karty):
    """
    Sprawdza, czy 'karty' (lista obiektów) tworzy SEKWENCJĘ z obsługą Jokerów.
    - >=3 karty
    - 1 kolor w normalnych
    - brak duplikatów wartości
    - luki wewnątrz <= liczba jokerów
    - As=14 (domyślnie), jokery wypełniają brakujące wartości.
    """
    if len(karty) < 3:
        return False

    jokers = [c for c in karty if c["name"].startswith("Joker")]
    normal = [c for c in karty if not c["name"].startswith("Joker")]
    jokers_count = len(jokers)

    if not normal:
        # same jokery => min 3 => sekwencja
        return len(karty) >= 3

    # kolor
    splitted = [c["name"].split() for c in normal]
    colors = {sp[1] for sp in splitted}
    if len(colors) != 1:
        return False

    # wartości
    valmap = {"J":11, "Q":12, "K":13, "A":14}
    nums = []
    for c in normal:
        first = c["name"].split()[0]
        if first.isdigit():
            nums.append(int(first))
        else:
            nums.append(valmap.get(first, 0))
    nums.sort()

    # duplikaty => false
    for i in range(len(nums)-1):
        if nums[i] == nums[i+1]:
            return False

    min_v = nums[0]
    max_v = nums[-1]

    needed = 0
    for i in range(len(nums)-1):
        gap = nums[i+1] - nums[i] - 1
        if gap < 0:
            return False
        needed += gap

    if needed > jokers_count:
        return False

    block_len = (max_v - min_v + 1)
    leftover = jokers_count - needed
    final_len = block_len + leftover

    return final_len >= 3


# -------------------------------------------------
#   Punktacja z As=1/10 i Jokerem
# -------------------------------------------------

def compute_group_points(group):
    """
    Oblicza punkty dla grupy (set lub sekwencja) z regułami:
      - As w secie => 10
      - As w sekwencji => 1, jeśli niskie (As–2–3),
                          inaczej 10
      - Joker => wartość karty, którą zastępuje
    """
    if is_set(group):
        return compute_points_for_set(group)
    elif is_sequence(group):
        return compute_points_for_sequence(group)
    else:
        return 0

def compute_points_for_set(group):
    """
    Set np. [9 Kier, 9 Trefl, Joker] => Joker=9 => 9+9+9
    Jeśli to set Asów => 10 each
    """
    jokers = [c for c in group if c["name"].startswith("Joker")]
    normal = [c for c in group if not c["name"].startswith("Joker")]

    if not normal:
        # same jokery => np. 3 => set Asów => 10 each
        return len(group)*10

    val_str = normal[0]["name"].split()[0]
    if val_str in ["A","As"]:
        # set asów => 10 each
        return len(group)*10
    else:
        base_pts = base_card_points(val_str)
        return len(normal)*base_pts + len(jokers)*base_pts


def compute_points_for_sequence(group):
    """
    Sekwencja: odtwarzamy spójny ciąg, jokery wypełniają luki,
    As=1 jeśli As i 2 w sekwencji (niskie), w przeciwnym razie 10.
    """
    jokers = [c for c in group if c["name"].startswith("Joker")]
    normal = [c for c in group if not c["name"].startswith("Joker")]

    if not normal:
        # np. 3 jokery => np. 2,3,4 => 9 pkt
        return 12 if len(group)==3 else 0

    valmap = {"J":11, "Q":12, "K":13, "A":14}
    nums = []
    for c in normal:
        first = c["name"].split()[0]
        if first.isdigit():
            nums.append(int(first))
        else:
            nums.append(valmap.get(first, 0))
    nums.sort()

    # ile luk?
    needed = 0
    for i in range(len(nums)-1):
        gap = nums[i+1] - nums[i] -1
        needed += gap

    jokers_count = len(jokers)
    leftover_jokers = jokers_count - needed
    # heurystyka As=1, jeśli as i '2' w sekwencji
    has_ace = any(c["name"].split()[0] in ["A","As"] for c in normal)
    has_two = any(c["name"].split()[0] == "2" for c in normal)
    ace_value = 10
    if has_ace and has_two:
        ace_value = 1

    min_v = nums[0]
    max_v = nums[-1]
    assigned_vals = []
    normal_vals = set(nums)

    # wypełniamy luki
    jleft = jokers_count
    for v in range(min_v, max_v+1):
        if v in normal_vals:
            assigned_vals.append(v)
        else:
            assigned_vals.append(v)  # Joker= v
            jleft -= 1

    total = 0
    for v in assigned_vals:
        if v == 14:
            total += ace_value
        elif v>=11:
            total += 10
        else:
            total += v
    return total

def base_card_points(val_str):
    """
    Bazowa wartość:
      '5' => 5
      'J/Q/K/A' => 10
      'Joker' => 0
    Bez logiki As=1/10.
    """
    if val_str.isdigit():
        return int(val_str)
    if val_str in ["J","Q","K","A"]:
        return 10
    if val_str.startswith("Joker"):
        return 0
    return 0

# -------------------------------------------------
#   Backtracking + liczenie sumy
# -------------------------------------------------

def znajdz_grupowanie(karty):
    """
    Rozkłada listę obiektów (karty) na sety i sekwencje (z Jokerami).
    Zwraca (True, total_points, [grupy]) lub (False, 0, None).
      total_points liczone wg compute_group_points
      (As=1/10, Joker = karta zastępowana).
    """
    solution = backtrack_groups(karty)
    if solution is None:
        return (False, 0, None)
    else:
        sum_points = 0
        for g in solution:
            sum_points += compute_group_points(g)
        return (True, sum_points, solution)

def backtrack_groups(cards):
    if not cards:
        return []

    import itertools
    n = len(cards)

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
    Sortuje karty w grupie rosnąco po wartości (2..14),
    Jokery na koniec.
    """
    valmap = {"J":11, "Q":12, "K":13, "A":14}
    def card_value(c):
        first = c["name"].split()[0]
        if first.startswith("Joker"):
            return 99
        if first.isdigit():
            return int(first)
        return valmap.get(first, 0)
    return sorted(group, key=card_value)
