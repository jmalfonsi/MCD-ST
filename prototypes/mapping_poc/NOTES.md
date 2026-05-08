# Verdict prototype mapping POC

## Question

Peut-on valider le principe d'un mapping automatisé MCD-ST sans interface graphique, à partir de plusieurs exports hétérogènes de logiciel SPSTi ?

## Résultat

Oui, le principe tient.

Le prototype démontre une chaîne minimale :

1. génération de plusieurs exports sources synthétiques ;
2. profilage des fichiers et colonnes ;
3. inférence des entités métier probables ;
4. détection des champs sensibles S4 à exclure du MCD standardisé ;
5. proposition de mapping scoré ;
6. génération d'un YAML de mapping ;
7. dry-run vers des tables MCD-ST ;
8. rapport qualité minimal.

## Tables générées

- `travailleur`
- `entreprise`
- `etablissement`
- `unite_travail`
- `episode_poste`
- `visite_sante_travail`
- `conclusion_medicale`
- `exposition_professionnelle`

## Apprentissage principal

Le mapping doit être pensé comme une combinaison de :

- profilage technique ;
- reconnaissance d'entités métier ;
- correspondance champ source vers champ cible ;
- mapping de valeurs vers concepts ;
- classification de sensibilité ;
- génération YAML versionnable ;
- contrôle qualité avant validation.

Le POC confirme aussi que les champs S4 doivent être traités dès le profilage, avant toute tentative de mapping vers le MCD standardisé.

## Durcissement v2

Le prototype a été durci avec des exports plus proches d'un logiciel métier :

- noms de fichiers peu explicites : `export_01_individus`, `export_02_structures`, `export_03_actes`, `export_04_risques` ;
- noms de colonnes non alignés sur le MCD : `ClePers`, `CleAdh`, `Site`, `Jour`, `Nature`, `Decision`, `LibRisque` ;
- champs directs à exclure : `NomUsuel`, `Prenom`, `TelPortable`, `Adherent`, `Siret`, `CR` ;
- détection des jointures candidates entre fichiers ;
- séparation entre mapping de colonnes et mapping de valeurs ;
- sélection de la meilleure source par entité pour éviter de mélanger des champs issus de plusieurs fichiers ;
- contrôle qualité vérifiant que les colonnes mappées existent dans le fichier source déclaré ;
- file de revue humaine pour les champs sensibles ou semi-libres.

Résultat du run durci :

- 8 entités MCD-ST générées ;
- 5 jointures candidates détectées ;
- 6 groupes de mapping de valeurs ;
- 6 champs S4 exclus ;
- 2 propositions laissées en revue humaine : `Reserve -> restriction_flag` et `Adaptation -> amenagement_flag`.

Ce comportement est souhaitable : le moteur automatise les correspondances robustes, mais ne valide pas seul les champs sensibles ou interprétatifs.

## Durcissement v3

Le prototype ajoute maintenant une boucle de revue complète :

1. génération d'un `mapping_propose.yaml` ;
2. génération d'un `review_queue.yaml` ;
3. simulation de décisions humaines dans `review_decisions.yaml` ;
4. application des décisions dans `mapping_valide.yaml` ;
5. dry-run brouillon ;
6. dry-run validé.

Les champs `Reserve -> restriction_flag` et `Adaptation -> amenagement_flag` sont approuvés par la revue simulée. Le dry-run validé renseigne donc les restrictions et aménagements, alors que le dry-run brouillon les laisse à `false`.

Le jeu de données ajoute aussi des valeurs inconnues ou à cadrer :

- `avis complémentaire -> AVIS_COMPLEMENTAIRE` ;
- `occasionnelle -> OCCASIONNELLE` ;
- `Charge mentale -> CHARGE_MENTALE`.

Ces valeurs restent en alerte de revue métier, même après validation des colonnes. Cela distingue correctement deux niveaux :

- revue de colonnes : le champ source alimente-t-il le bon champ MCD ?
- revue de valeurs : les valeurs locales correspondent-elles à des concepts standardisés acceptés ?

Résultat du run v3 :

- 8 entités MCD-ST générées ;
- 5 jointures candidates ;
- 6 groupes de mapping de valeurs proposés avant revue ;
- 8 groupes de mapping de valeurs dans le mapping validé après ajout des deux champs revus ;
- 6 champs S4 exclus ;
- 0 proposition de mapping colonne en attente après revue ;
- 3 valeurs de nomenclature encore en revue métier.

## À durcir après le prototype

- gérer les exports Excel multi-onglets ;
- détecter les clés de jointure entre fichiers ;
- introduire une vraie file de revue humaine ;
- tester des noms de colonnes plus ambigus ;
- séparer mapping de colonnes et mapping de valeurs ;
- ajouter des packs par logiciel source ;
- brancher progressivement embeddings ou petit modèle de domaine.
- transformer la file de revue en entrées YAML validables ;
- gérer les entités alimentées par plusieurs sources avec jointures explicites ;
- ajouter des scénarios avec valeurs inconnues et champs manquants.
- ajouter une validation de nomenclature qui empêche certains exports analytiques tant que les valeurs critiques ne sont pas revues ;
- produire un mini-rapport Markdown lisible par un data manager ;
- préparer la forme d'un futur composant API.

## Absorption produit

Le POC est validé comme preuve de principe, mais son code reste jetable.

La décision produit durable est décrite dans [../../docs/MAPPING_ENGINE_SPEC.md](../../docs/MAPPING_ENGINE_SPEC.md). La prochaine étape n'est pas d'étendre indéfiniment ce script, mais d'en extraire les comportements validés vers un moteur MVP :

- profilage ;
- classification de sensibilité ;
- graphe des sources ;
- scoring des colonnes ;
- mapping de valeurs ;
- file de revue ;
- contrat YAML ;
- dry-run ;
- rapport qualité.

## Première extraction moteur

Une première extraction existe dans `src/mcdst`.

Elle reprend les comportements validés du POC sous forme de modules et d'une CLI :

- `mcdst mapping propose` ;
- `mcdst mapping review` ;
- `mcdst mapping apply`.

Le prototype reste utile comme démonstrateur bavard, mais le développement du moteur doit maintenant se faire dans le paquet `mcdst`.
