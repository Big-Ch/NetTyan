"""Generate short club dialogue without a model request."""
from collections import defaultdict, deque
from random import choice


class ClubDialogue:
    OPENINGS = (
        "Вот тебе домашка.",
        "У клуба для тебя маленькое дело.",
        "Посмотрим, что ты построишь без инструкции.",
        "Пора добавить миру одну бесполезную вещь.",
    )
    BUILDS = (
        "табурет для эндермена", "трон для курицы", "маяк для тех, кто потерялся дома",
        "кассу для магазина воздуха", "сейф для одного картофеля", "кабинку для переговоров с овцой",
        "музей одной палки", "сцену для молчаливого хора", "памятник понедельнику",
    )
    LIMITS = (
        "Лимит пять блоков.", "Лимит семь блоков.", "Бери два вида блоков.",
        "Оставь проход для курицы.", "Используй только то, что уже есть.",
    )
    ENDINGS = (
        "Дай постройке имя.", "Когда закончишь, придумай ей рекламу из трёх слов.",
        "Если выйдет криво, так и задумано.", "В конце подпиши своим именем.",
    )
    INVITATIONS = (
        "хочешь домашку от клуба?", "зайдёшь на одну постройку?", "есть минута для клуба?",
        "берёшь странное задание?",
    )
    ACCEPTANCES = (
        "Договорились.", "Хорошо. Теперь это твоя затея.",
        "Берёшь на себя самую странную стройку дня.", "Отлично. Посмотрим, что выйдет.",
    )
    FAREWELLS = (
        "Пас принят. Клуб переживёт. Пойду искать работу для себя.",
        "Договорились. У меня как раз есть собственная ерунда, которой пора заняться.",
        "Честный ответ. Ладно, пойду строить сам.",
        "Свободен. Даже табурет сегодня получил больше обязательств.",
    )

    def __init__(self):
        self.recent = defaultdict(lambda: deque(maxlen=2))

    def _pick(self, options):
        recent = self.recent[options]
        selected = choice([option for option in options if option not in recent])
        recent.append(selected)
        return selected

    def _task(self):
        build = self._pick(self.BUILDS)
        limit = self._pick(self.LIMITS)
        return f"На своём участке построй {build}. {limit}"

    def homework(self):
        return f"{self._pick(self.OPENINGS)} {self._task()} {self._pick(self.ENDINGS)}"

    def invitation(self, name):
        return f"{name}, {self._pick(self.INVITATIONS)} {self._task()} Можешь сказать «пас»."

    def acceptance(self):
        return f"{self._pick(self.ACCEPTANCES)} Когда закончишь, напиши «Тайлер, готово»."

    def farewell(self):
        return self._pick(self.FAREWELLS)
