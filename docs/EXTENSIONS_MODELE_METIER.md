# Domaines métier sensibles intégrés au MCD-ST v0.1

## Statut

Ces domaines font désormais partie du périmètre v0.1, sous forme minimale,
structurée et prudente.

La règle d'intégration est stricte :

- aucune pièce jointe, PDF, courrier ou compte rendu libre ;
- pas de texte médical libre dans les tables standardisées ;
- valeurs transformées en concepts, codes, classes, dates ou indicateurs simples ;
- sensibilité S3 par défaut, avec blocage S4 si un export contient un identifiant
  direct ou un commentaire libre ;
- fixtures uniquement synthétiques.

## Tables ajoutées au noyau v0.1

| Domaine | Table v0.1 | Rôle |
| --- | --- | --- |
| Clinique et biométrie | `examen_complementaire` | Résultat structuré d'examen, mesure ou biométrie |
| Pathologies, AT et MP | `pathologie_atmp` | Événement pathologie/AT/MP structuré et minimisé |
| Arrêts de travail | `arret_travail` | Période d'arrêt utile à la PDP et aux visites de reprise |
| Vaccinations | `vaccination` | Suivi vaccinal professionnel structuré |
| DUERP et risques collectifs | `risque_unite_travail` | Risque collectif évalué au niveau unité de travail |

## 1. Clinique, biométrie et examens complémentaires

Table : `examen_complementaire`.

Champs minimaux :

- `examen_id` ;
- `travailleur_id` ;
- `date_examen` ;
- `examen_type_concept_id` : audiogramme, spirométrie, IMC, tension, biométrologie ;
- `resultat_valeur` ;
- `resultat_unite` ;
- `interpretation_concept_id` ;
- `sensitivity_level` ;
- `source_id`.

Limites v0.1 :

- un résultat par ligne ;
- pas de courbe, image, PDF ou compte rendu ;
- unités conservées et à normaliser progressivement via vocabulaire.

## 2. Pathologies, accidents du travail et maladies professionnelles

Table : `pathologie_atmp`.

Champs minimaux :

- `pathologie_atmp_id` ;
- `travailleur_id` ;
- `date_evenement` ;
- `type_evenement` : AT, MP, ATMP, pathologie ;
- `code_cim10` si disponible ;
- `pathologie_concept_id` ;
- `reconnaissance_flag` ;
- `sensitivity_level` ;
- `source_id`.

Limites v0.1 :

- pas de diagnostic libre ;
- pas de détail médico-légal ;
- le code CIM-10 reste optionnel et doit être traité comme qualité variable.

## 3. Arrêts de travail

Table : `arret_travail`.

Champs minimaux :

- `arret_travail_id` ;
- `travailleur_id` ;
- `date_debut` ;
- `date_fin` ;
- `type_arret` ;
- `lie_atmp_flag` ;
- `sensitivity_level` ;
- `source_id`.

Limites v0.1 :

- données déclaratives acceptées mais tracées ;
- pas de motif médical libre ;
- type d'arrêt à normaliser progressivement.

## 4. Vaccinations

Table : `vaccination`.

Champs minimaux :

- `vaccination_id` ;
- `travailleur_id` ;
- `vaccin_concept_id` ;
- `date_vaccination` ;
- `statut_vaccinal` ;
- `rappel_prevu` ;
- `sensitivity_level` ;
- `source_id`.

Limites v0.1 :

- suivi vaccinal professionnel uniquement ;
- référentiel vaccinal minimal au départ ;
- pas de copie du carnet vaccinal complet.

## 5. Risques collectifs et DUERP

Table : `risque_unite_travail`.

Champs minimaux :

- `risque_unite_travail_id` ;
- `etablissement_id` ;
- `unite_travail_id` ;
- `risque_concept_id` ;
- `niveau_risque` ;
- `mesure_prevention_source` ;
- `date_evaluation` ;
- `sensitivity_level` ;
- `source_id`.

Limites v0.1 :

- granularité unité de travail par défaut ;
- contenu DUERP structuré uniquement ;
- pas de commentaire libre sur des personnes ou situations nominatives.

## Implémentation MVP

Le scénario synthétique `mapping_poc_exports` contient désormais cinq exports
additionnels :

- `export_05_biometrie.csv` ;
- `export_06_pathologies_atmp.csv` ;
- `export_07_arrets.csv` ;
- `export_08_vaccinations.csv` ;
- `export_09_duerp.csv`.

Ces exports alimentent le mapping, la revue, le dry-run et les tests
d'acceptation du moteur.
