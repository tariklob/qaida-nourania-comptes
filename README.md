# Qaïda Nourania — Version 3 (professeur unique, classe unique)

## Organisation
- Un seul compte professeur administrateur, initialisé au premier lancement.
- Une seule classe : tous les comptes élèves créés par le professeur appartiennent à ce groupe.
- Chaque élève possède son propre identifiant et son mot de passe.
- Le professeur consulte les statistiques globales et le détail de chaque élève.

## Fonctionnalités de cette version
- Connexion professeur / élève.
- Création de comptes élèves avec mot de passe temporaire généré.
- Changement obligatoire du mot de passe temporaire à la première connexion.
- Parcours de démonstration en 10 leçons.
- Affichage des mots arabes vocalisés, audio par synthèse vocale du navigateur.
- Saisie en arabe et clavier virtuel (lettres et signes vocaliques).
- Vérification exacte du texte normalisé Unicode, sans supprimer les harakats.
- Enregistrement de chaque tentative et de chaque réussite dans SQLite.
- Tableau de bord professeur avec statistiques et détail par élève.

## Installation locale (Windows)
1. Installe Python 3.10 ou plus récent.
2. Décompresse le ZIP.
3. Ouvre PowerShell dans le dossier `qaida_nourania`.
4. Crée l'environnement :
   `python -m venv .venv`
5. Active-le :
   `.venv\Scripts\Activate.ps1`
6. Installe les dépendances :
   `pip install -r requirements.txt`
7. Configure les variables avant le premier lancement :
   ```powershell
   $env:SECRET_KEY="remplace-par-une-cle-aleatoire-longue"
   $env:TEACHER_USERNAME="professeur"
   $env:TEACHER_PASSWORD="un-mot-de-passe-long-et-unique"
   python app.py
   ```
8. Ouvre `http://127.0.0.1:5000`.

Le compte professeur est créé au premier démarrage si `TEACHER_PASSWORD` est défini. Garde ces identifiants privés.

## Déploiement sur Internet
Ce ZIP ne constitue pas encore un site public. Pour que les élèves se connectent depuis chez eux ou l'établissement, il faut déployer l'application sur un hébergeur compatible Flask, configurer les variables d'environnement et activer HTTPS.
Pour un usage réel, utilise une base PostgreSQL ou un stockage persistant, définis `COOKIE_SECURE=1`, protège les secrets, effectue des sauvegardes et limite les tentatives de connexion.

## Limites importantes
- Les mots et la progression sont un contenu de démonstration à faire valider par un enseignant compétent en Qaïda Nourania.
- L'audio utilise la voix arabe installée sur l'appareil ; sa qualité et sa prononciation pédagogique ne sont pas garanties. Des enregistrements validés par un enseignant sont préférables.
- La comparaison est stricte après normalisation Unicode NFC et retrait du tatwîl. Elle compare les caractères et signes vocaliques ; elle ne réalise pas encore une analyse linguistique des variantes d'écriture.
- Le correcteur indique les caractères saisis qui correspondent ou non à la référence, mais l'alignement visuel reste un outil d'aide et non un diagnostic linguistique.
- Avant toute utilisation avec des mineurs, prévoir la protection des données, une information adaptée, les autorisations requises par l'établissement/familles et une politique de confidentialité.
