# Logique Détaillée pour Amélioration 3 : Gestion Recherche par SIREN (Scénario 2)

Ce document décrit les modifications à apporter à la fonction `main()` du script `enrich_insee_data.py` pour la gestion améliorée des recherches par SIREN (Scénario 2), ainsi que la modification nécessaire pour la fonction `get_data_by_siren`.

## Contexte de l'Amélioration

Lorsque l'on recherche une entreprise par son SIREN (si le SIRET source est invalide ou manquant) et que l'API INSEE retourne plusieurs établissements pour ce SIREN, il est nécessaire d'appliquer une logique de filtrage et de sélection pour déterminer quelles informations utiliser pour enrichir la ligne principale, et comment gérer les cas d'ambiguïté persistante.

## Modification de la Fonction `get_data_by_siren`

Pour que la logique ci-dessous dans `main()` fonctionne correctement, la fonction `get_data_by_siren(siren: str, api_token: str, champs: list = None)` **doit impérativement être modifiée** pour retourner systématiquement :

*   `None` : En cas d'erreur lors de l'appel API.
*   Une **liste** (potentiellement vide) de **dictionnaires d'établissements intégralement parsés** : En cas de succès de l'appel API. Chaque dictionnaire dans la liste doit contenir les informations combinées de l'établissement et de son unité légale parente (c'est-à-dire, le résultat de `parse_etablissement_data` déjà enrichi des données de `parse_unite_legale_data`).

**Logique interne suggérée pour `get_data_by_siren` :**
1.  Appeler l'API INSEE avec l'endpoint `/siren/{siren}`.
2.  Si l'appel échoue, retourner `None`.
3.  Parser les informations de l'objet `uniteLegale` principal de la réponse JSON.
4.  Vérifier si la réponse JSON contient une liste d'établissements (souvent sous `uniteLegale.etablissements` ou une clé similaire, ou parfois l'API `/siren` ne retourne que le siège ou une liste limitée).
    *   **Si une liste d'établissements est explicitement fournie dans la réponse `/siren` :** Pour chaque établissement JSON brut dans cette liste, le parser en utilisant `parse_etablissement_data`, en lui fournissant les données de l'unité légale déjà parsées. Retourner cette liste d'établissements parsés.
    *   **Si la réponse `/siren` ne détaille que l'unité légale et son `siretSiege` (sans lister tous les établissements) :** Pour assurer un retour cohérent (une liste d'établissements), `get_data_by_siren` devrait alors effectuer un appel interne à `get_data_by_siret(siretSiege, api_token, champs)` pour récupérer les détails complets de l'établissement siège. Ensuite, parser cet établissement siège et le retourner dans une liste contenant ce seul élément.
    *   **Si aucun établissement n'est trouvé ou si l'UL est radiée sans établissements actifs :** Retourner une liste vide `[]`.

## Modification de la Logique du Scénario 2 dans `main()`

Dans la fonction `main()`, au sein de la boucle `for index, row in df.iterrows():`, la section pour le Scénario 2 (recherche par SIREN) doit être révisée comme suit :

```python
    # ... (après Scénario 1 : recherche par SIRET)

    # Scénario 2 (SIREN)
    # (processed_data_for_row est None si Scénario 1 n'a pas abouti)
    elif not processed_data_for_row and pd.notna(siren_val) and len(siren_val) == 9 and siren_val.isdigit():
        print(f"INFO: Ligne {index + 1}: SIRET invalide/manquant ou non concluant. Tentative par SIREN: '{siren_val}'")

        # get_data_by_siren retourne maintenant une LISTE d'établissements parsés, ou None/[]
        etablissements_pour_siren = get_data_by_siren(siren_val, args.api_token, champs=DEFAULT_INSEE_FIELDS)

        if etablissements_pour_siren is None: # Erreur API
            status_msg = "INSEE: Erreur API - SIREN"
        elif not etablissements_pour_siren: # Liste vide = SIREN non trouvé ou sans établissements.
            status_msg = "INSEE: SIREN non trouvé (aucun étab.)"
        elif len(etablissements_pour_siren) == 1:
            # Un seul établissement trouvé pour ce SIREN.
            single_etab = etablissements_pour_siren[0]
            ul_status = single_etab.get("INSEE_StatutAdministratifUL")
            etab_status = single_etab.get("INSEE_EtatAdministratifEtablissement")
            is_active = (ul_status == 'A' and etab_status == 'A')

            if is_active:
                processed_data_for_row = single_etab
                status_msg = "OK - SIREN (1 étab. actif)"
            else:
                status_msg = "INSEE: SIREN trouvé (1 étab. inactif)"
                inactive_entry = row.to_dict()
                for key, value in single_etab.items(): # Assumer que single_etab contient les clés préfixées INSEE_
                    inactive_entry[f"INSEE_Candidat_{key.replace('INSEE_', '')}"] = value # Adapter le préfixe si besoin
                inactive_matches_accumulator.append(inactive_entry)
        else:
            # Plusieurs établissements trouvés pour le SIREN.
            # Logique de filtrage par ville et/ou choix du siège.

            city_source = str(row.get(col_address_city, '')).strip() # col_address_city doit être défini au début de main

            candidate_etabs_after_city_filter = list(etablissements_pour_siren) # Copie pour modification potentielle

            if city_source:
                city_source_normalized = city_source.upper() # Adapter la normalisation si nécessaire

                temp_filtered_etabs = []
                for etab in etablissements_pour_siren:
                    etab_city_api = str(etab.get("INSEE_LibelleCommuneEtablissement", '')).upper()
                    if etab_city_api == city_source_normalized:
                        temp_filtered_etabs.append(etab)

                print(f"INFO: Ligne {index + 1}: SIREN {siren_val} a {len(etablissements_pour_siren)} étab. initiaux. Filtre par ville '{city_source_normalized}' retient {len(temp_filtered_etabs)} étab.")

                if temp_filtered_etabs: # Si le filtre par ville donne au moins un résultat
                    candidate_etabs_after_city_filter = temp_filtered_etabs
                    status_msg = f"INSEE: Plusieurs étab. SIREN (ville correspondante: {len(candidate_etabs_after_city_filter)})"
                else:
                    # Filtre par ville n'a rien donné, on ignore le filtre (on garde tous les candidats initiaux)
                    print(f"INFO: Ligne {index + 1}: Filtre par ville pour SIREN {siren_val} n'a rien retenu. Conservation des {len(etablissements_pour_siren)} établissements initiaux.")
                    status_msg = "INSEE: Plusieurs étab. SIREN (ville non concordante)"
                    # candidate_etabs_after_city_filter reste etablissements_pour_siren (la copie initiale)
            else:
                # Pas de ville source, on travaille avec tous les établissements du SIREN
                status_msg = "INSEE: Plusieurs étab. SIREN (ville source absente)"
                # candidate_etabs_after_city_filter reste etablissements_pour_siren

            # Maintenant, traiter candidate_etabs_after_city_filter
            if len(candidate_etabs_after_city_filter) == 1:
                single_etab_to_process = candidate_etabs_after_city_filter[0]
                ul_status = single_etab_to_process.get("INSEE_StatutAdministratifUL")
                etab_status = single_etab_to_process.get("INSEE_EtatAdministratifEtablissement")
                is_active = (ul_status == 'A' and etab_status == 'A')

                if is_active:
                    processed_data_for_row = single_etab_to_process
                    # Raffiner le statut basé sur le chemin pris
                    if city_source and temp_filtered_etabs: # A été filtré par ville avec succès
                         status_msg = "OK - SIREN (ville correspond, 1 actif)"
                    else: # Soit pas de ville source, soit filtre ville n'a rien donné mais on est tombé à 1 par autre moyen (improbable ici)
                         status_msg = "OK - SIREN (1 étab. actif)" # Fallback
                else: # Candidat unique mais inactif
                    if city_source and temp_filtered_etabs:
                        status_msg = "INSEE: SIREN (ville correspond, 1 inactif)"
                    else:
                        status_msg = "INSEE: SIREN (1 étab. inactif)" # Fallback

                    inactive_entry = row.to_dict()
                    for key, value in single_etab_to_process.items():
                        inactive_entry[f"INSEE_Candidat_{key.replace('INSEE_', '')}"] = value
                    inactive_matches_accumulator.append(inactive_entry)

            elif len(candidate_etabs_after_city_filter) > 1:
                # Il reste plusieurs établissements. On cherche le siège.
                # La conversion en str(X).lower() == 'true' gère les booléens et les chaînes 'True'/'False'
                siege_etablissements = [e for e in candidate_etabs_after_city_filter if str(e.get("INSEE_EstSiege", "false")).lower() == 'true']

                if len(siege_etablissements) == 1:
                    # Un seul siège trouvé
                    single_siege = siege_etablissements[0]
                    ul_status = single_siege.get("INSEE_StatutAdministratifUL")
                    etab_status = single_siege.get("INSEE_EtatAdministratifEtablissement")
                    is_active = (ul_status == 'A' and etab_status == 'A')

                    if is_active:
                        processed_data_for_row = single_siege
                        status_msg = "OK - SIREN (siège trouvé, actif)"
                    else:
                        status_msg = "INSEE: SIREN (siège trouvé, inactif)"
                        inactive_entry = row.to_dict()
                        for key, value in single_siege.items():
                            inactive_entry[f"INSEE_Candidat_{key.replace('INSEE_', '')}"] = value
                        inactive_matches_accumulator.append(inactive_entry)
                else:
                    # Pas de siège unique (0 ou >1) ou filtre par ville a laissé >1 candidats.
                    # Conformément à la réponse utilisateur : dispatcher tous ces candidats restants.
                    # Le statut sera "INSEE: Plusieurs étab. SIREN (dispatch vers annexes)" ou plus spécifique.
                    # Si city_source était présent et a filtré, et qu'il reste >1: "INSEE: Plusieurs étab. SIREN (même ville, pas de siège unique)"
                    # Si city_source était absent ou n'a pas filtré, et qu'il reste >1: "INSEE: Plusieurs étab. SIREN (pas de siège unique)"

                    if city_source and temp_filtered_etabs and len(candidate_etabs_after_city_filter) > 1 : # temp_filtered_etabs a été utilisé et > 1
                        status_msg = "INSEE: Plusieurs étab. SIREN (même ville, sans siège unique)"
                    elif len(candidate_etabs_after_city_filter) > 1 : # Pas de filtre ville concluant ou pas de ville source, et > 1 étab. sans siège unique
                        status_msg = "INSEE: Plusieurs étab. SIREN (autres villes ou sans siège clair)"
                    # else: status_msg reste celui défini avant le bloc if/elif len(candidate_etabs_after_city_filter)

                    active_candidates = []
                    inactive_candidates = []
                    for etab_candidate in candidate_etabs_after_city_filter: # Utiliser la liste potentiellement filtrée par ville
                        ul_s = etab_candidate.get("INSEE_StatutAdministratifUL")
                        et_s = etab_candidate.get("INSEE_EtatAdministratifEtablissement")
                        is_cand_active = (ul_s == 'A' and et_s == 'A')
                        if is_cand_active:
                            active_candidates.append(etab_candidate)
                        else:
                            inactive_candidates.append(etab_candidate)

                    if active_candidates:
                        for ac in active_candidates:
                            entry = row.to_dict()
                            for k, v in ac.items(): entry[f"INSEE_Candidat_{k.replace('INSEE_', '')}"] = v
                            multiple_matches_accumulator.append(entry)
                        # Ajuster le statut si besoin
                        if not inactive_candidates and len(active_candidates) > 1: # Uniquement des actifs multiples
                             status_msg = status_msg.replace("(dispatch vers annexes)", "(tous actifs, voir multiples)")

                    if inactive_candidates:
                        for ic in inactive_candidates:
                            entry = row.to_dict()
                            for k, v in ic.items(): entry[f"INSEE_Candidat_{k.replace('INSEE_', '')}"] = v
                            inactive_matches_accumulator.append(entry)
                        # Ajuster le statut si besoin
                        if not active_candidates and len(inactive_candidates) > 1: # Uniquement des inactifs multiples
                             status_msg = status_msg.replace("(dispatch vers annexes)", "(tous inactifs, voir inactifs)")
    # ... (fin du Scénario 2)
```

Points Clés de cette Logique :
*   **Modification de `get_data_by_siren` :** Elle doit impérativement retourner une liste d'établissements parsés (chacun contenant les infos de l'UL et de l'établissement).
*   **Traitement d'une liste d'établissements :** La logique dans `main` gère les cas où `get_data_by_siren` retourne 0, 1, ou plusieurs établissements.
*   **Filtrage par ville :** Si plusieurs établissements sont retournés et une ville source est disponible, un filtrage est tenté.
    *   Si le filtre par ville donne des résultats, cette sous-liste est utilisée.
    *   Si le filtre par ville ne donne aucun résultat, la liste originale complète des établissements est conservée.
*   **Priorité au siège :** Après le filtrage par ville (ou si pas de ville), si plusieurs établissements demeurent, on cherche un unique établissement siège.
*   **Dispatch final :** Si, après tous ces filtres, un seul établissement est identifié, il est utilisé pour enrichir la ligne principale (en vérifiant son statut actif/inactif). Si plusieurs établissements subsistent, ils sont tous dispatchés vers les fichiers annexes (`multiple_matches_file` pour les actifs, `inactive_matches_file` pour les inactifs) et la ligne principale reçoit un statut indiquant cette multiplicité.

Cette logique est conçue pour suivre vos dernières spécifications.

```
