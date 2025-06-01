# Enrichissement de Données d'Entreprises avec l'API SIRENE INSEE

## Objectif du Script

Le script `enrich_insee_data.py` a pour objectif d'enrichir un fichier CSV contenant des informations d'entreprises (SIRET, SIREN, nom) en interrogeant l'API SIRENE V3 de l'INSEE. Il permet de récupérer des informations à jour et de les ajouter au fichier initial.

## Prérequis

*   Python 3.x
*   Bibliothèques Python : `pandas`, `requests`

## Installation des Dépendances

Pour installer les bibliothèques nécessaires, exécutez la commande suivante :
```bash
pip install pandas requests
```

## Utilisation (Ligne de Commande)

Le script s'exécute en ligne de commande avec les arguments suivants :

```bash
python enrich_insee_data.py -i <fichier_entree.csv> -o <fichier_sortie_enrichi.csv> -t <votre_jeton_api> -m <fichier_correspondances_multiples.csv>
```

### Arguments :

*   `-i, --input-file <fichier_entree.csv>` : (Requis) Chemin vers le fichier CSV d'entrée contenant les données à enrichir.
*   `-o, --output-file <fichier_sortie_enrichi.csv>` : (Requis) Chemin pour sauvegarder le fichier CSV principal, enrichi avec les données de l'INSEE.
*   `-t, --api-token <votre_jeton_api>` : (Requis) Votre jeton d'accès personnel (clé API) pour l'API SIRENE V3 de l'INSEE.
*   `-m, --multiple-matches-file <fichier_correspondances_multiples.csv>` : (Requis) Chemin pour sauvegarder un fichier CSV séparé listant les cas où une recherche par nom a retourné plusieurs correspondances d'établissements.

## Format du Fichier d'Entrée Attendu

*   Le fichier d'entrée doit être au format CSV.
*   Pour un enrichissement optimal, les colonnes suivantes sont recommandées (bien que le script puisse fonctionner si certaines sont manquantes/vides pour certaines lignes) :
    *   `Siret` : Numéro SIRET (14 chiffres) de l'établissement. Utilisé en priorité pour la recherche.
    *   `siren` : Numéro SIREN (9 chiffres) de l'unité légale. Utilisé si le SIRET n'est pas fourni ou n'a pas donné de résultat.
    *   `nom_entreprise_normalise` : Nom normalisé de l'entreprise. Utilisé pour la recherche si ni SIRET ni SIREN n'ont abouti. (Actuellement, la recherche par nom se base sur le champ `denominationUniteLegale` de l'API).
*   D'autres colonnes présentes dans le fichier source seront conservées dans les fichiers de sortie.

## Description des Fichiers de Sortie

1.  **Fichier de sortie enrichi (`--output-file`)** :
    *   Contient toutes les colonnes du fichier d'entrée.
    *   Colonnes additionnelles préfixées par `INSEE_` contenant les données récupérées de l'API. Les principales colonnes ajoutées incluent :
        *   `INSEE_SIRET` : SIRET de l'établissement trouvé.
        *   `INSEE_SIREN_UL` : SIREN de l'unité légale.
        *   `INSEE_DenominationUniteLegale` : Dénomination/raison sociale de l'unité légale.
        *   `INSEE_DenominationUsuelleEtablissement` : Dénomination usuelle de l'établissement (si disponible, sinon reprend la dénomination de l'UL).
        *   `INSEE_Adresse_Complete` : Adresse postale complète et formatée de l'établissement.
        *   `INSEE_CodePostalEtablissement` : Code postal de l'établissement.
        *   `INSEE_LibelleCommuneEtablissement` : Nom de la commune de l'établissement.
        *   `INSEE_EstSiege` : Booléen (`True`/`False`) indiquant si l'établissement est le siège social.
        *   `INSEE_NumeroTVA` : Numéro de TVA intracommunautaire de l'unité légale (si disponible).
        *   `INSEE_StatutAdministratifUL` : Statut administratif de l'unité légale (A = Actif, C = Cessé).
        *   `INSEE_EtatAdministratifEtablissement` : État administratif de l'établissement (A = Actif, F = Fermé).
        *   `INSEE_DateSuppressionUniteLegale` : Date de suppression de l'unité légale (si applicable).
        *   `INSEE_CaractereEmployeurEtablissement`: Caractère employeur de l'établissement (O = Oui, N = Non).
    *   `Statut_API_INSEE` : Colonne indiquant le résultat de l'interrogation API pour chaque ligne (ex: "OK - SIRET", "INSEE: Non trouvé par nom", "INSEE: Plusieurs par nom", "INSEE: SIRET non trouvé/Erreur", etc.).

2.  **Fichier des correspondances multiples (`--multiple-matches-file`)** :
    *   Ce fichier est créé uniquement si une ou plusieurs recherches par nom retournent plusieurs établissements candidats (après application du filtre "actif" côté client).
    *   Chaque ligne de ce fichier correspond à un candidat potentiel pour une ligne du fichier source.
    *   Il contient :
        *   Toutes les colonnes de la ligne source originale du fichier d'entrée.
        *   Une colonne `original_row_index_in_input` indiquant l'index (0-based) de la ligne originale dans le fichier d'entrée.
        *   Toutes les colonnes d'information INSEE (préfixées `INSEE_`) pour le candidat spécifique.

## Gestion du Jeton API

**Important** : Votre jeton d'accès à l'API INSEE est personnel et confidentiel.
*   **Ne l'écrivez pas en dur** dans le script si vous prévoyez de partager le code ou de le versionner.
*   Pour une utilisation en production ou partagée, il est fortement recommandé d'utiliser des méthodes plus sécurisées pour gérer les jetons, telles que :
    *   Variables d'environnement.
    *   Fichiers de configuration non versionnés (ex: `.env`).
    *   Solutions de gestion de secrets.
Le script actuel requiert que le jeton soit passé en argument de ligne de commande (`-t` ou `--api-token`). Assurez-vous de la sécurité de cet argument lors de l'exécution.
```
