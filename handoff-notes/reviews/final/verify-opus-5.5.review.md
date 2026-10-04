To powiadomienie dotyczy pierwszego, porzuconego przebiegu porównania. Druga połowa tego przebiegu (wersja rodzica) w ogóle nie wystartowała, bo jej worktree już nie istniał. Kod wyjścia 1 pochodzi wyłącznie z mojego źle zapisanego `tail -1`. Wyniki z poprzedniego raportu opierają się na powtórzonym przebiegu z zapisem do /opt/data/cache/wm-out/, więc werdykty się nie zmieniają.

Sprawdziłem, czy ten stary przebieg nie zostawił pliku head.json w repozytorium: hermes-webui ma czysty `git status`, pliku nie ma.
