# Demandes de Clarification (Version 2) pour l'Intégration API INSEE

Suite à vos dernières propositions d'amélioration, voici quelques points à clarifier pour finaliser la logique du script `enrich_insee_data.py` :

**Concernant l'Amélioration 2 (Recherche par nom/ville et la nouvelle gestion du filtrage "actif") :**

Vous avez indiqué : *"Le filtrage sur les unités actives doit aussi être supprimé : si les unités sont actives, elles sont écrites dans le fichier des correspondances multiples sinon si les entités ne sont pas actives, elles écrites dans le fichiers des entités non actives."*

Cela implique que la fonction `search_data_by_name` (et sa future variante nom/ville) ne filtrera plus elle-même les résultats sur le statut "actif". Elle retournera tous les candidats trouvés par l'API. C'est ensuite la logique principale dans `main()` qui dispatchera les résultats.

Mes questions sont :

1.  **Cas d'un unique candidat trouvé par recherche par nom (ou nom/ville) :**
    *   Si ce candidat unique est **inactif** (selon les données INSEE comme `INSEE_StatutAdministratifUL` ou `INSEE_EtatAdministratifEtablissement`), doit-il :
        *   Option 2.1 : Être écrit dans le **fichier principal enrichi** (`args.output_file`), avec son statut d'inactivité visible grâce aux colonnes INSEE ?
        *   Option 2.2 : Être écrit directement dans le fichier des **entités inactives** (`inactive_matches_insee.csv`), et la ligne dans le fichier principal n'est pas enrichie avec ce candidat (ou reçoit un statut "INSEE: Trouvé inactif") ?
    *   *Votre préférence (2.1 ou 2.2) ?*

2.  **Cas de plusieurs candidats trouvés par recherche par nom (ou nom/ville) :**
    *   Si l'API retourne une liste de candidats (un mélange possible d'actifs et d'inactifs) :
        *   Est-ce que la ligne source originale est dupliquée dans le fichier `multiple_matches_file.csv` (celui pour les "actifs" ou "ambigus") pour **chaque candidat actif** trouvé ?
        *   ET, est-ce que la ligne source originale est *également* dupliquée dans le nouveau fichier `inactive_matches_insee.csv` pour **chaque candidat inactif** trouvé parmi ces mêmes résultats ?
        *   En d'autres termes, une seule recherche par nom pour une ligne source peut-elle potentiellement alimenter à la fois `multiple_matches_file.csv` (pour ses candidats actifs) et `inactive_matches_insee.csv` (pour ses candidats inactifs) ?
    *   *Veuillez confirmer cette logique de dispatch ou la corriger.*

**Concernant l'Amélioration 3 (Filtrage par ville pour la recherche par SIREN retournant plusieurs établissements) :**

Vous avez indiqué : *"Si après ce filtrage [par ville], aucun établissement n'est retenu alors il faut ignorer ce filtre et conserver tous les candidats."*

Mes questions sont :

3.  **Choix de l'établissement après avoir ignoré le filtre par ville :**
    *   Si, après avoir ignoré le filtre par ville (parce qu'il n'a rien donné), on se retrouve toujours avec **plusieurs établissements** pour le SIREN donné :
        *   Comment choisit-on l'établissement dont les données enrichiront la ligne dans le fichier principal ?
        *   Doit-on prioriser l'établissement siège (celui où `INSEE_EstSiege` est vrai) ?
        *   S'il n'y a pas de siège clairement identifié parmi les candidats restants, ou s'il y a plusieurs sièges (peu probable mais possible), que fait-on ? Prend-on le premier de la liste ?
        *   Ou bien, dans ce cas d'ambiguïté persistante (plusieurs établissements pour un SIREN, même après tentative de filtre par ville infructueuse), tous ces établissements restants devraient-ils plutôt aller dans le fichier `multiple_matches_file.csv` (s'ils sont actifs) et/ou `inactive_matches_insee.csv` (s'ils sont inactifs), sans qu'aucun n'enrichisse directement la ligne principale ?
    *   *Veuillez décrire la règle de décision souhaitée dans ce cas.*

Vos réponses à ces questions me permettront de définir précisément l'algorithme avant de générer le nouveau plan de développement.
```
