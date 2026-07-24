# Notif ressorties cinéma (Allociné)

Envoie une notification sur ton téléphone dès qu'un film de ta liste
apparaît dans les séances Allociné à Paris / petite couronne.

⚠️ **Limite honnête** : Allociné n'a pas d'API publique officielle. Ce script
utilise une librairie communautaire (`allocine-seances`) qui scrape leur
site. Ça fonctionne aujourd'hui, mais ça peut casser si Allociné change son
site — dans ce cas il faudra ajuster le script.

## Mise en place (10-15 min, une seule fois)

1. **Installer l'app [ntfy](https://ntfy.sh/)** sur ton téléphone (iOS/Android,
   gratuite, pas de compte requis).
2. Dans l'app, **s'abonner à un "topic"** — choisis un nom unique et un peu
   secret (ex: `films-julien-8k2j`), personne d'autre ne doit deviner ce nom.
3. **Créer un repo GitHub** (gratuit) et y déposer ces 4 fichiers en gardant
   la structure :
   ```
   check_films.py
   films.txt
   README.md
   .github/workflows/check.yml
   ```
4. Dans le repo GitHub → **Settings → Secrets and variables → Actions** →
   New repository secret :
   - Nom : `NTFY_TOPIC`
   - Valeur : le nom de topic choisi à l'étape 2
5. Édite **`films.txt`** avec tes films (un titre par ligne).
6. Onglet **Actions** du repo → active les workflows si demandé → tu peux
   lancer "Run workflow" manuellement pour tester tout de suite.

Le script tourne ensuite automatiquement chaque jour à 9h (heure de Paris)
et ne notifie que les **nouvelles** séances (pas de doublons).

## Personnaliser

- **Zone géographique** : modifie `DEPARTEMENTS_A_SURVEILLER` dans
  `check_films.py` (ex: ajouter `"Rhône"` pour Lyon). Attention : plus de
  départements = plus de requêtes = script plus lent.
- **Fréquence** : modifie la ligne `cron` dans `.github/workflows/check.yml`.
- **Nombre de jours vérifiés à l'avance** : `JOURS_A_VERIFIER` dans
  `check_films.py`.

## Tester en local avant de déployer

```bash
pip install allocine-seances requests
export NTFY_TOPIC="ton-topic-secret"
python check_films.py
```
