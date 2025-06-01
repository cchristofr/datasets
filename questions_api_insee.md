# Questions pour l'intégration de l'API SIREN INSEE

Voici les 7 points sur lesquels nous avons besoin de vos précisions pour bien intégrer l'API SIREN de l'INSEE dans le script de traitement des données d'entreprises :

1.  **Accès à l'API SIREN de l'INSEE :**
    *   **Information attendue :**
        *   Possédez-vous une **clé API (ou token/jeton d'accès)** pour l'API SIREN de l'INSEE ? (Veuillez répondre par Oui/Non)
        *   Si Oui, connaissez-vous les **limites d'utilisation** de cette clé (par exemple, le nombre d'appels autorisés par seconde ou par jour) ? (Veuillez répondre par Oui/Non, et si Oui, fournir une approximation des limites si possible)

2.  **Utilisation des données retournées par l'API :**
    *   **Information attendue :** Lorsque l'API INSEE retourne des informations (nom de l'entreprise, adresse, numéro de TVA), comment souhaitez-vous les utiliser par rapport aux données déjà présentes dans votre fichier ?
        *   **Option A : Remplacer** les données existantes par celles de l'INSEE ?
        *   **Option B : Ajouter de nouvelles colonnes** dédiées pour les données INSEE (par exemple : `Nom_INSEE`, `Adresse_INSEE`, `TVA_INSEE`, `EstSiege_INSEE`) afin de pouvoir comparer ?
        *   **Option C : Une approche mixte** (par exemple, si un champ comme l'adresse est vide dans votre fichier, le remplir avec la donnée INSEE ; sinon, choisir quelle source prioriser ou garder les deux) ?
        *   *Veuillez indiquer votre préférence (A, B, C) ou décrire votre besoin spécifique.*

3.  **Choix du nom pour la recherche (pour le 3ème scénario – si ni SIREN ni SIRET valide n'est disponible) :**
    *   **Information attendue :** Si le script doit rechercher une entreprise par son nom auprès de l'API INSEE, quel nom doit-il utiliser ?
        *   Le nom **brut** tel qu'il apparaît dans votre colonne `Supplier` ?
        *   Ou le nom **normalisé** (calculé par le script, stocké dans `nom_entreprise_normalise`) ?
        *   *Veuillez indiquer votre préférence.*

4.  **Gestion des "aucun candidat trouvé" (pour le 3ème scénario – recherche par nom) :**
    *   **Information attendue :** Si une recherche par nom via l'API INSEE ne retourne aucun résultat, comment souhaitez-vous que cela soit indiqué dans le fichier de résultats principal ?
        *   Par exemple, en inscrivant une note comme "INSEE: Non trouvé par nom" dans une **nouvelle colonne de statut** ? Ou avez-vous une autre préférence ?
        *   *Veuillez décrire comment signaler cette absence de résultat.*

5.  **Format de l'adresse retournée par l'API :**
    *   **Information attendue :** Avez-vous connaissance du format dans lequel l'API SIREN de l'INSEE retourne les adresses postales ?
        *   Est-ce un **champ unique** contenant toute l'adresse ?
        *   Ou l'adresse est-elle **structurée** en plusieurs parties (numéro, type de voie, nom de voie, code postal, ville) ?
        *   *(Si vous n'avez pas cette information, ce n'est pas un problème ; je la rechercherai dans la documentation officielle de l'API. Mais si vous le savez, cela peut accélérer la planification.)*

6.  **Contenu du fichier des correspondances multiples (pour le 3ème scénario – recherche par nom retournant plusieurs candidats) :**
    *   **Information attendue :** Si une recherche par nom retourne plusieurs entreprises candidates, un fichier CSV séparé sera créé. Veuillez spécifier :
        *   Quelles **colonnes de votre fichier source original** souhaitez-vous voir répétées pour chaque candidat dans ce fichier ? (Exemple : toutes les colonnes, ou une sélection comme `Supplier`, `Tax Number 1`, etc.)
        *   Quelles **informations spécifiques issues de l'API pour chaque candidat** doivent être incluses dans ce fichier ? (Exemple : Nom du candidat INSEE, SIRET du candidat, Adresse complète du candidat, Numéro de TVA du candidat, Indication si c'est le siège social pour le candidat).
        *   *Veuillez lister les noms des colonnes que vous souhaitez voir dans ce fichier d'export des correspondances multiples.*

7.  **Utilisation des SIREN/SIRET existants (pour les scénarios 1 et 2 – recherche par SIREN/SIRET) :**
    *   **Information attendue :** Ceci est une confirmation. Pour les recherches par SIREN ou SIRET via l'API, nous utiliserons bien les numéros SIREN/SIRET que le script a **préalablement extraits et validés** à partir de vos colonnes `Tax Number 1`, `Tax Number 2`, etc., exact ? (Veuillez répondre par Oui/Non)
```
