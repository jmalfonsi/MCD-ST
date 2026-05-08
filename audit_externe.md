


**Chef de projet :** Notre objectif est de construire le meilleur Modèle Commun de Données en Santé au Travail (MCD-ST) possible. On ignore les contraintes de temps, de budget et les formalités administratives de l'AMI BOAS. On se concentre sur la robustesse technique et la pertinence médicale. Comment on gère l'hétérogénéité massive des bases SPSTi ?

**Data engineer :** L'architecture en 5 couches (RAW, Mapping, Modèle commun, Qualité, Cohorting) est la bonne. Le passage par des fichiers de configuration YAML pour le mapping source-cible est indispensable pour ne pas hardcoder les spécificités de chaque logiciel métier. Tout doit finir en format Parquet pour les performances de requêtage. 

**Médecin du travail :** Le mapping YAML ne suffira pas pour la clinique. Les conclusions médicales (restrictions, aménagements, inaptitudes) et les motifs de visite sont souvent saisis en texte libre ou semi-structuré. Si on ne nettoie pas ça, nos cohortes ne vaudront rien.

**IPRP / expert exposition :** Même constat pour les expositions professionnelles et les intitulés de postes. Les nomenclatures locales sont un enfer. Le document parle d'un "module IA optionnel" pour structurer les textes courts. Il ne doit pas être optionnel. Il est central.

**Data scientist :** Je suis d'accord. Je passe le module IA en prérequis. On partira sur une approche hybride : expressions régulières et règles expertes pour le gros du volume, et classification supervisée (NLP) pour le reste. Mais cela exige que le Médecin et l'IPRP annotent manuellement un corpus massif (bien plus que les 200 à 500 lignes visées initialement) pour entraîner les modèles.

**Médecin du travail :** C'est acté, on annotera le volume nécessaire. La qualité de la donnée de sortie en dépend.

**DPO / juriste RGPD :** Attention au texte libre. Il contient des noms propres, des noms d'entreprises, des données hautement sensibles. L'entraînement et l'inférence du modèle IA doivent se faire strictement en local. Aucune donnée réelle, même pseudonymisée, ne doit remonter vers un serveur central.

**Data engineer :** C'est réglé par la conteneurisation. On package tout l'ETL, le moteur de qualité et l'IA sous Docker. Le SPSTi fait tourner l'image sur sa propre infrastructure. Rien ne sort.

**DPO / juriste RGPD :** Quid de l'open source et des tests publics ? 

**Data scientist :** On utilisera le générateur de données synthétiques prévu dans le pipeline. 

**DPO / juriste RGPD :** Ces données synthétiques devront passer des tests de robustesse contre la ré-identification. Un simple brassage de variables ne suffit pas, il faut garantir la destruction des liens statistiques uniques. Je validerai l'algorithme de synthèse.

**Chef de projet :** Décisions validées : 1. Pipeline 100% Dockerisé en local. 2. Module IA de traitement du langage naturel rendu obligatoire. 3. Génération de données synthétiques sous contrôle strict du DPO. Passons au moteur de cohorting.

**Data scientist :** L'exemple de définition de cohorte en YAML (ex: `biomech_return_restriction_2024`) est trop statique. Il faut intégrer la profondeur longitudinale. Pour évaluer la prévention de la désinsertion professionnelle (PDP), il faut pouvoir requêter une chronologie : s'assurer que l'exposition *précède* l'événement de santé ou la restriction.

**Data engineer :** Je vais développer un parseur qui traduit ces règles YAML en requêtes SQL fenêtrées complexes sur nos tables Parquet. Ça permettra de gérer la temporalité (avant/après, délais entre visites) sans que l'utilisateur n'ait à coder en SQL.
